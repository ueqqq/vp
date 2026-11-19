import sys, datetime, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import schema, cuba
from core.schema import BY_KEY, SETTINGS, parse, render_template, parse_presence, resolve_color, SettingValues
from core.store import Store


class ParseTests(unittest.TestCase):
    def test_int_bounds(self):
        s = BY_KEY["vote_goal"]
        self.assertEqual(parse(s, "300"), (300, None))
        self.assertIsNotNone(parse(s, "5")[1])
        self.assertIsNotNone(parse(s, "99999")[1])
        self.assertIsNotNone(parse(s, "abc")[1])
        self.assertIsNotNone(parse(s, "")[1])

    def test_bool_english_and_spanish(self):
        s = BY_KEY["module_music"]
        for word in ("on", "Yes", "sí", "SI", "true", "1"):
            self.assertEqual(parse(s, word), (True, None), word)
        for word in ("off", "No", "false", "0"):
            self.assertEqual(parse(s, word), (False, None), word)
        self.assertIsNotNone(parse(s, "maybe")[1])

    def test_choice_and_theme(self):
        self.assertEqual(parse(BY_KEY["theme"], "Palma"), ("palma", None))
        self.assertIsNotNone(parse(BY_KEY["theme"], "neon")[1])
        self.assertEqual(parse(BY_KEY["default_language"], "ES"), ("es", None))

    def test_color(self):
        s = BY_KEY["accent_color"]
        self.assertEqual(parse(s, "#cf142b"), ("#CF142B", None))
        self.assertEqual(parse(s, "002a8f"), ("#002A8F", None))  # hash is optional
        self.assertEqual(parse(s, ""), ("", None))  # empty means "use the theme"
        self.assertIsNotNone(parse(s, "#12345")[1])
        self.assertIsNotNone(parse(s, "red")[1])

    def test_timezone(self):
        s = BY_KEY["quote_timezone"]
        self.assertEqual(parse(s, "America/Havana"), ("America/Havana", None))
        self.assertIsNotNone(parse(s, "Mars/Olympus")[1])

    def test_text_empty_rules(self):
        self.assertIsNotNone(parse(BY_KEY["nation_name"], "")[1])  # name can't be blank
        self.assertEqual(parse(BY_KEY["motto"], ""), ("", None))  # motto can
        self.assertIsNotNone(parse(BY_KEY["nation_name"], "x" * 41)[1])

    def test_template_placeholders_validated(self):
        s = BY_KEY["ping_message"]
        self.assertIsNone(parse(s, "{role} only {remaining} left!")[1])
        err = parse(s, "hello {username}")[1]
        self.assertIn("{username}", err)
        self.assertIn("{remaining}", err)  # tells you what IS allowed

    def test_presence_lines(self):
        s = BY_KEY["presence_lines"]
        value, err = parse(s, "watching: over Cuba\nlistening: son cubano\n\nplain line")
        self.assertIsNone(err)
        self.assertEqual(parse_presence(value), [("watching", "over Cuba"), ("listening", "son cubano"), ("watching", "plain line")])
        self.assertIsNotNone(parse(s, "\n".join("x" for _ in range(9)))[1])
        self.assertIsNotNone(parse(s, "y" * 61)[1])
        self.assertEqual(parse_presence("shouting: hi"), [("watching", "shouting: hi")])  # unknown verb kept as text


class RenderTests(unittest.TestCase):
    def test_known_and_unknown(self):
        self.assertEqual(render_template("Hola {name} de {nation}", name="Ana", nation="Cuba"), "Hola Ana de Cuba")
        self.assertEqual(render_template("{oops} {name}", name="Ana"), "{oops} Ana")  # typo never crashes
        self.assertEqual(render_template("**{remaining}** left", remaining=0), "**0** left")

    def test_color_resolution(self):
        self.assertEqual(resolve_color("bandera", ""), schema.THEMES["bandera"])
        self.assertEqual(resolve_color("bandera", "#112233")[0], 0x112233)
        self.assertEqual(resolve_color("nonsense", ""), schema.THEMES["bandera"])
        self.assertEqual(resolve_color("roja", "garbage")[0], schema.THEMES["roja"][0])


class SchemaIntegrityTests(unittest.TestCase):
    def test_every_default_passes_its_own_validation(self):
        """A shipped default that the validator rejects would be a bug waiting for an admin to hit."""
        for s in SETTINGS:
            raw = "on" if s.kind == "bool" and s.default else "off" if s.kind == "bool" else str(s.default)
            value, err = parse(s, raw)
            self.assertIsNone(err, f"{s.key}: {err}")

    def test_keys_unique_and_grouped(self):
        keys = [s.key for s in SETTINGS]
        self.assertEqual(len(keys), len(set(keys)))
        for s in SETTINGS:
            self.assertIn(s.group, schema.GROUPS, s.key)
        self.assertLessEqual(max(sum(1 for s in SETTINGS if s.group == g) for g in schema.GROUPS), 25)  # fits one select menu

    def test_template_defaults_only_use_allowed_placeholders(self):
        for s in SETTINGS:
            if s.kind == "template":
                self.assertEqual(schema._token_names(s.default) - set(s.placeholders), set(), s.key)


class ValueStoreTests(unittest.TestCase):
    def test_defaults_set_reset_and_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d)); v = SettingValues(store)
            self.assertEqual(v.get(1, "vote_goal"), BY_KEY["vote_goal"].default)
            self.assertTrue(v.is_default(1, "vote_goal"))
            self.assertEqual(v.set(1, "vote_goal", "400"), (True, "Saved."))
            self.assertEqual(v.get(1, "vote_goal"), 400)
            self.assertEqual(v.get(2, "vote_goal"), BY_KEY["vote_goal"].default)  # per-server
            ok, msg = v.set(1, "vote_goal", "-3")
            self.assertFalse(ok)
            self.assertEqual(v.get(1, "vote_goal"), 400)  # a rejected value changes nothing
            self.assertFalse(v.set(1, "nope", "x")[0])
            store.flush_sync()
            self.assertEqual(SettingValues(Store(Path(d))).get(1, "vote_goal"), 400)
            self.assertTrue(v.reset(1, "vote_goal"))
            self.assertEqual(v.get(1, "vote_goal"), BY_KEY["vote_goal"].default)
            self.assertFalse(v.reset(1, "vote_goal"))

    def test_coexists_with_existing_channel_and_role_data(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d))
            store.data("settings", {})["7"] = {"channels": {"welcome": 5}, "roles": {"staff": 9}}  # saved by an older version
            v = SettingValues(store)
            v.set(7, "theme", "roja")
            g = store.data("settings")["7"]
            self.assertEqual(g["channels"], {"welcome": 5})
            self.assertEqual(g["roles"], {"staff": 9})
            self.assertEqual(g["values"]["theme"], "roja")


class CubaTests(unittest.TestCase):
    def test_content_complete_in_both_languages(self):
        for kind, items in cuba.KINDS.items():
            self.assertGreaterEqual(len(items), 8, kind)
            for item in items:
                self.assertTrue(item["en"].strip() and item["es"].strip(), item)
        for item in cuba.SLANG:
            self.assertTrue(item["term"] and item["example"])
        terms = [s["term"].lower() for s in cuba.SLANG]
        self.assertEqual(len(terms), len(set(terms)))

    def test_word_of_day_is_stable_and_cycles(self):
        d = datetime.date(2026, 11, 18)
        self.assertEqual(cuba.word_of_day(d), cuba.word_of_day(d))
        seen = {cuba.word_of_day(d + datetime.timedelta(days=i))["term"] for i in range(len(cuba.SLANG))}
        self.assertEqual(len(seen), len(cuba.SLANG))  # every word gets its turn

    def test_find_slang_forgiving(self):
        self.assertEqual(cuba.find_slang("Asere")["term"], "asere")
        self.assertEqual(cuba.find_slang("que bola")["term"], "¿Qué bolá?")  # no accents needed
        self.assertEqual(cuba.find_slang("ÑO")["term"], "ñó")
        self.assertEqual(cuba.find_slang("¿qué bolá?")["term"], "¿Qué bolá?")
        self.assertEqual(cuba.find_slang("qué bolá")["term"], "¿Qué bolá?")
        self.assertIsNone(cuba.find_slang("nonexistent"))


if __name__ == "__main__":
    unittest.main()
