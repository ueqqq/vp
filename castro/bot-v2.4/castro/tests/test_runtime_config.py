import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.schema import BY_KEY, display_value
from votes.engine import VoteEngine, new_state, CLOSE, NORMAL

SITES = ["A", "B", "C"]


class ConfigureTests(unittest.TestCase):
    def test_changing_goal_moves_target_not_progress(self):
        e = VoteEngine(new_state(250), SITES, 250, 30)
        e.apply({"A": 100, "B": 100, "C": 100}, 1)
        e.apply({"A": 200, "B": 100, "C": 100}, 2)
        self.assertEqual((e.progress, e.remaining), (100, 150))
        e.configure(500, 30)
        self.assertEqual((e.progress, e.remaining), (100, 400))  # progress kept
        self.assertEqual(e.state["goal"], 500)
        e.configure(100, 30)  # lowering below current progress completes it on the next reading
        r = e.apply({"A": 201, "B": 100, "C": 100}, 3)
        self.assertTrue(r.completed)

    def test_changing_ping_threshold_changes_phase(self):
        e = VoteEngine(new_state(250), SITES, 250, 30)
        e.apply({"A": 0, "B": 0, "C": 0}, 1)
        e.apply({"A": 200, "B": 0, "C": 0}, 2)  # 50 remaining
        self.assertNotEqual(e.phase(2), CLOSE)
        e.configure(250, 60)
        self.assertEqual(e.phase(2), CLOSE)
        self.assertTrue(e.apply({"A": 201, "B": 0, "C": 0}, 3).should_ping)

    def test_lowered_goal_with_progress_does_not_ping_spuriously_twice(self):
        e = VoteEngine(new_state(250), SITES, 250, 30)
        e.apply({"A": 0, "B": 0, "C": 0}, 1)
        e.apply({"A": 230, "B": 0, "C": 0}, 2)
        self.assertTrue(e.apply({"A": 231, "B": 0, "C": 0}, 3).should_ping)
        e.mark_pinged()
        self.assertFalse(e.apply({"A": 232, "B": 0, "C": 0}, 4).should_ping)


class DisplayTests(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(display_value(BY_KEY["module_music"], True), "✅ on")
        self.assertEqual(display_value(BY_KEY["module_music"], False), "❌ off")
        self.assertEqual(display_value(BY_KEY["motto"], ""), "—")
        long = display_value(BY_KEY["welcome_message"], BY_KEY["welcome_message"].default, 50)
        self.assertEqual(len(long), 50)
        self.assertTrue(long.endswith("…"))
        self.assertNotIn("\n", display_value(BY_KEY["presence_lines"], "a\nb"))


if __name__ == "__main__":
    unittest.main()
