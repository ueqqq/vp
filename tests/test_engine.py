import sys, unittest, tempfile, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from votes.engine import VoteEngine, new_state, try_claim, WAITING, NORMAL, MOMENTUM, CLOSE, FINAL, CELEBRATION
from votes.parsing import parse_count

SITES = ["A", "B", "C"]


def make(goal=250, threshold=30, **kw):
    return VoteEngine(new_state(goal), SITES, goal, threshold, **kw)


class EngineTests(unittest.TestCase):
    def test_waits_until_majority_of_sites_read(self):
        e = make()
        # Only one site → still waiting (majority of 3 is 2)
        e.apply({"A": 100, "B": None, "C": None}, 1)
        self.assertFalse(e.ready)
        self.assertEqual(e.phase(1), WAITING)
        # Two sites → ready (majority)
        e.apply({"A": 100, "B": 200, "C": None}, 2)
        self.assertTrue(e.ready)
        self.assertEqual(e.progress, 0)
        self.assertEqual(e.remaining, 250)
        # Third site arriving later is accepted; large jump may complete a cycle
        r = e.apply({"A": 100, "B": 200, "C": 50}, 3)
        self.assertTrue(e.ready)
        self.assertEqual(e.progress, 50)  # new site contributes 50 above the original baseline
        self.assertFalse(r.completed)

    def test_progress_and_phases(self):
        e = make()
        e.apply({"A": 100, "B": 100, "C": 100}, 1)
        e.apply({"A": 150, "B": 100, "C": 100}, 2)
        self.assertEqual(e.progress, 50)
        self.assertEqual(e.phase(2), NORMAL)
        e.apply({"A": 200, "B": 150, "C": 100}, 3)
        self.assertEqual(e.progress, 150)
        self.assertEqual(e.phase(3), MOMENTUM)
        r = e.apply({"A": 250, "B": 170, "C": 100}, 4)
        self.assertEqual(e.remaining, 30)
        self.assertEqual(e.phase(4), CLOSE)
        self.assertTrue(r.should_ping)
        e.mark_pinged()
        r = e.apply({"A": 260, "B": 170, "C": 100}, 5)
        self.assertEqual(e.remaining, 20)
        self.assertFalse(r.should_ping)  # only pinged once per cycle
        e.apply({"A": 270, "B": 170, "C": 100}, 6)
        self.assertEqual(e.phase(6), FINAL)

    def test_completion_carries_overflow_and_resets_ping(self):
        e = make()
        e.apply({"A": 0, "B": 0, "C": 0}, 1)
        e.state["ping_sent"] = True
        r = e.apply({"A": 260, "B": 0, "C": 0}, 2)  # 10 over the goal
        self.assertTrue(r.completed)
        self.assertEqual(e.state["cycle"], 2)
        self.assertEqual(e.progress, 10)  # overflow carried into the new cycle
        self.assertFalse(e.state["ping_sent"])
        self.assertEqual(e.phase(3), CELEBRATION)
        self.assertEqual(len(e.state["parties"]), 1)

    def test_backwards_reading_rejected(self):
        e = make()
        e.apply({"A": 500, "B": 500, "C": 500}, 1)
        r = e.apply({"A": 12, "B": 500, "C": 500}, 2)  # the old '13,456 -> 13' style bug
        self.assertIn("A", r.rejected)
        self.assertEqual(e.state["counts"]["A"], 500)
        self.assertEqual(e.progress, 0)

    def test_huge_jump_needs_confirmation(self):
        e = make(max_jump=500)
        e.apply({"A": 1000, "B": 1000, "C": 1000}, 1)
        r = e.apply({"A": 9000, "B": 1000, "C": 1000}, 2)
        self.assertIn("A", r.rejected)
        self.assertEqual(e.state["counts"]["A"], 1000)
        r = e.apply({"A": 9000, "B": 1000, "C": 1000}, 3)  # same value twice -> trusted
        self.assertIn("A", r.accepted)
        self.assertEqual(e.state["counts"]["A"], 9000)

    def test_failed_site_marked_stale_not_fresh(self):
        e = make(stale_after=900)
        e.apply({"A": 1, "B": 1, "C": 1}, 0)
        e.apply({"A": 2, "B": None, "C": 2}, 1000)
        self.assertEqual(e.stale_sites(1000), ["B"])
        self.assertEqual(e.state["counts"]["B"], 1)  # last known value kept

    def test_set_remaining_and_rebase(self):
        e = make()
        e.apply({"A": 1000, "B": 1000, "C": 1000}, 1)
        self.assertTrue(e.set_remaining(20, 2))
        self.assertEqual(e.remaining, 20)
        self.assertTrue(e.state["ping_sent"])  # already inside ping range, don't spam
        e.rebase(3)
        self.assertEqual(e.remaining, 250)
        self.assertFalse(make().set_remaining(10, 1))  # no readings yet

    def test_survives_partial_saved_state(self):
        e = VoteEngine({"baseline": 5, "counts": {"A": 5, "B": 5, "C": 5}}, SITES, 250, 30)
        self.assertTrue(e.ready)
        self.assertEqual(e.state["cycle"], 1)


class ClaimTests(unittest.TestCase):
    def test_limit_and_cooldown(self):
        p = {}
        self.assertEqual(try_claim(p, 1, 0, 3, 3600)[:2], (True, "ok"))
        ok, reason, wait = try_claim(p, 1, 100, 3, 3600)
        self.assertEqual((ok, reason), (False, "cooldown"))
        self.assertGreater(wait, 3000)
        try_claim(p, 1, 4000, 3, 3600)
        try_claim(p, 1, 8000, 3, 3600)
        self.assertEqual(try_claim(p, 1, 12000, 3, 3600)[:2], (False, "limit"))
        self.assertEqual(p["claims_total"], 3)

    def test_new_cycle_resets_cycle_count_not_lifetime(self):
        p = {}
        for i in range(3):
            try_claim(p, 1, i * 4000, 3, 3600)
        self.assertEqual(try_claim(p, 2, 20000, 3, 3600)[:2], (True, "ok"))
        self.assertEqual(p["claims_cycle"], 1)
        self.assertEqual(p["claims_total"], 4)


class ParseTests(unittest.TestCase):
    def test_thousands_separator(self):
        self.assertEqual(parse_count("<b>13,456 Votes - All time</b>", [r"<b>(\d[\d,]*)\s+Votes\s*-\s*All time</b>"]), 13456)

    def test_falls_through_patterns(self):
        pats = [r"nope(\d+)", r"Vote\(s\)[^0-9]{0,50}(\d[\d,]*)"]
        self.assertEqual(parse_count("<strong>Vote(s)</strong></td><td>  1,234 </td>", pats), 1234)

    def test_no_match_is_none(self):
        self.assertIsNone(parse_count("<html>cloudflare challenge</html>", [r"(\d+) votes"]))


if __name__ == "__main__":
    unittest.main()
