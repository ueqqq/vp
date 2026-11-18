import sys, asyncio, json, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.store import Store


class StoreTests(unittest.TestCase):
    def test_roundtrip_and_atomic_write(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store(Path(d))
            s.data("x", {})["a"] = 1
            s.save("x")
            asyncio.run(s.flush())
            self.assertEqual(json.loads((Path(d) / "x.json").read_text())["a"], 1)
            self.assertFalse(list(Path(d).glob("*.tmp")))
            self.assertEqual(Store(Path(d)).data("x")["a"], 1)

    def test_corrupt_file_is_moved_aside_not_lost(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x.json").write_text("{not json")
            s = Store(Path(d))
            self.assertEqual(s.data("x", {"fresh": True}), {"fresh": True})
            self.assertEqual(len(list(Path(d).glob("x.corrupt-*.json"))), 1)

    def test_background_flush_starts_and_close_flushes(self):
        async def run(d):
            s = Store(Path(d))
            await s.start(interval=0.05)
            s.data("y", {})["k"] = "v"
            s.save("y")
            await asyncio.sleep(0.2)
            self.assertEqual(json.loads((Path(d) / "y.json").read_text())["k"], "v")
            s.data("y")["k"] = "w"
            s.save("y")
            await s.close()
            self.assertEqual(json.loads((Path(d) / "y.json").read_text())["k"], "w")
        with tempfile.TemporaryDirectory() as d:
            asyncio.run(run(d))


if __name__ == "__main__":
    unittest.main()
