import io
import json
import unittest
from argparse import Namespace
from unittest import mock

from giellaltlextools import gtlemmatest
from giellaltlextools.gtlemmatest import check_lemma, generation_failures


class FakeFst:
    """Duck-typed stand-in for the hfst/pyhfst lookup objects."""

    def __init__(self, table):
        self.table = table

    def lookup(self, form):
        return self.table.get(form, [])


class TestGenerationFailures(unittest.TestCase):
    def test_pass_when_a_tag_regenerates_the_lemma(self):
        gen = FakeFst({"beavdi+N+Sg+Nom": [("beavdi", 0.0)]})
        no_gen, wrong, empty, matched = generation_failures(
            "beavdi", ["+N+Sg+Nom"], gen)
        self.assertEqual(no_gen, [])
        self.assertEqual(wrong, [])
        self.assertFalse(empty)
        self.assertTrue(matched)

    def test_extra_wrong_form_recorded_even_when_lemma_matches(self):
        gen = FakeFst({
            "beavdi+N+Sg+Nom": [("beavdi", 0.0)],
            "beavdi+N+Pl+Nom": [("beavttit", 0.0)],
        })
        _, wrong, _, matched = generation_failures(
            "beavdi", ["+N+Sg+Nom", "+N+Pl+Nom"], gen)
        self.assertTrue(matched)
        self.assertEqual(
            wrong, [{"expected": "beavdi+N+Pl+Nom", "got": "beavttit"}])

    def test_no_generation(self):
        no_gen, wrong, empty, matched = generation_failures(
            "kaaffe", ["+N+Sg+Nom", "+N+Pl+Nom"], FakeFst({}))
        self.assertEqual(no_gen, ["kaaffe+N+Sg+Nom", "kaaffe+N+Pl+Nom"])
        self.assertEqual(wrong, [])
        self.assertTrue(empty)
        self.assertFalse(matched)


class TestCheckLemma(unittest.TestCase):
    def test_pass_returns_none_and_writes_nothing(self):
        log = io.StringIO()
        gen = FakeFst({"run+V+Inf": [("run", 0.0)]})
        result = check_lemma("run", ["+V+Inf"], gen, FakeFst({}), log, False)
        self.assertIsNone(result)
        self.assertEqual(log.getvalue(), "")

    def test_no_generation_record_and_markdown(self):
        log = io.StringIO()
        analyser = FakeFst({"kaffe": [("kaffe+N", 0.0)]})
        result = check_lemma("kaffe", ["+N+Sg+Nom"], FakeFst({}), analyser,
                             log, False)
        self.assertEqual(result["lemma"], "kaffe")
        self.assertEqual(result["no_generation"], ["kaffe+N+Sg+Nom"])
        self.assertEqual(result["wrong_generation"], [])
        self.assertEqual(result["analyses"], ["kaffe+N"])
        self.assertTrue(result["empty"])
        md = log.getvalue()
        self.assertIn("**kaffe** failures:", md)
        self.assertIn("`kaffe+N+Sg+Nom` does not generate!", md)
        self.assertIn("* `kaffe` has following analyses:", md)
        self.assertIn("  * `kaffe+N`", md)

    def test_wrong_generation_record(self):
        log = io.StringIO()
        gen = FakeFst({"uure+N+Sg+Nom": [("uurre", 0.0)]})
        result = check_lemma("uure", ["+N+Sg+Nom"], gen, FakeFst({}), log,
                             False)
        self.assertEqual(result["wrong_generation"],
                         [{"expected": "uure+N+Sg+Nom", "got": "uurre"}])
        self.assertFalse(result["empty"])
        self.assertIn("`uure+N+Sg+Nom` => `uurre`", log.getvalue())
        self.assertIn("`uure` has no analyses either", log.getvalue())


class TestJsonOutput(unittest.TestCase):
    CONFIG = {
        "generator": "/build/generator-gt-norm.hfstol",
        "analyser": "/build/analyser-gt-norm.hfstol",
        "nouns": {
            "lexcfile": "/src/stems/nouns.lexc",
            "lemmatags": ["+N+Sg+Nom", "+N+Pl+Nom"],
        },
    }

    def _run(self, generator, analyser, lemmas, **overrides):
        opts = Namespace(
            pos="nouns", driver="subprocess", verbose=False, debug=False,
            threshold=0, oov_limit=10_000, time_out=60, editor=None,
            config=io.StringIO(json.dumps(self.CONFIG)),
            jsonfile=io.StringIO(), logfile=io.StringIO(),
        )
        for key, value in overrides.items():
            setattr(opts, key, value)
        with mock.patch.object(gtlemmatest, "load_hfst_pope",
                               side_effect=[generator, analyser]), \
             mock.patch.object(gtlemmatest, "scrapelemmas",
                               return_value=lemmas), \
             mock.patch("builtins.open", mock.mock_open(read_data="")):
            gtlemmatest.dostuff(opts, opts.logfile)
        opts.jsonfile.seek(0)
        return json.load(opts.jsonfile), opts.logfile.getvalue()

    def test_json_matches_markdown_run(self):
        generator = FakeFst({
            "beavdi+N+Sg+Nom": [("beavdi", 0.0)],
            "beavdi+N+Pl+Nom": [("beavddit", 0.0)],
            # "gáffe" generates nothing
        })
        analyser = FakeFst({"gáffe": [("gáffe+N+Sg+Loc", 0.0)]})
        data, md = self._run(generator, analyser, ["beavdi", "gáffe"])

        self.assertEqual(data["pos"], "nouns")
        self.assertEqual(data["lexc"], "nouns.lexc")
        self.assertEqual(data["lemmas"], 2)
        self.assertEqual(data["tested"], 2)
        self.assertEqual(data["ungenerated"], 1)   # gáffe
        self.assertFalse(data["truncated"])
        self.assertEqual([f["lemma"] for f in data["failures"]], ["gáffe"])
        self.assertEqual(data["failures"][0]["no_generation"],
                         ["gáffe+N+Sg+Nom", "gáffe+N+Pl+Nom"])
        self.assertEqual(data["failures"][0]["analyses"], ["gáffe+N+Sg+Loc"])
        self.assertIn("nouns.lexc", data["settings"]["nouns"]["lexcfile"])
        # markdown still produced
        self.assertIn("**gáffe** failures:", md)
        self.assertIn("## Lemma statistics", md)

    def test_truncated_flag_on_oov_limit(self):
        data, _ = self._run(FakeFst({}), FakeFst({}),
                            ["a", "b", "c"], oov_limit=2, threshold=-10_000)
        self.assertTrue(data["truncated"])


if __name__ == "__main__":
    unittest.main()
