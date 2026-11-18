import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.polls import new_poll, cast, tally, winners, is_expired, close, parse_options
from core.paginate import paginate


def poll(n=3):
    return new_poll("1", "Q?", [f"opt{i}" for i in range(n)], 1, 0, 100)


class PollTests(unittest.TestCase):
    def test_one_vote_per_person_changeable(self):
        p = poll()
        self.assertEqual(cast(p, 5, 0), "ok")
        self.assertEqual(cast(p, 5, 0), "same")
        self.assertEqual(cast(p, 5, 2), "changed")
        self.assertEqual(tally(p), [0, 0, 1])  # moved, not duplicated
        cast(p, 6, 2)
        self.assertEqual(tally(p), [0, 0, 2])

    def test_invalid_and_closed(self):
        p = poll()
        self.assertEqual(cast(p, 1, 9), "invalid")
        self.assertEqual(cast(p, 1, -1), "invalid")
        close(p, 50)
        self.assertEqual(cast(p, 1, 0), "closed")
        self.assertEqual(tally(p), [0, 0, 0])

    def test_expiry(self):
        p = poll()
        self.assertFalse(is_expired(p, 99))
        self.assertTrue(is_expired(p, 100))
        close(p, 100)
        self.assertFalse(is_expired(p, 200))  # already closed

    def test_winners_and_ties(self):
        p = poll()
        self.assertEqual(winners(p), [])
        cast(p, 1, 1); cast(p, 2, 2)
        self.assertEqual(winners(p), [1, 2])
        cast(p, 3, 2)
        self.assertEqual(winners(p), [2])

    def test_parse_options(self):
        self.assertEqual(parse_options("Yes\nNo\n\n yes ")[0], ["Yes", "No"])  # blank + duplicate dropped
        self.assertEqual(parse_options("1. Red\n2) Blue\n- Green")[0], ["Red", "Blue", "Green"])
        self.assertEqual(parse_options("2024 election\n10 more years")[0], ["2024 election", "10 more years"])
        self.assertIsNotNone(parse_options("Only one")[1])
        self.assertIsNotNone(parse_options("a\nb\nc\nd\ne")[1])
        self.assertIsNotNone(parse_options("a\n" + "x" * 81)[1])

    def test_paginate(self):
        self.assertEqual(paginate([], 5), [])
        self.assertEqual(paginate(list(range(11)), 5), [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10]])
        self.assertEqual(paginate([1, 2], 0), [[1], [2]])


if __name__ == "__main__":
    unittest.main()
