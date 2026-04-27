import io
import unittest

from giellaltlextools.gtspelltest import DEFAULT_EXCLUSIONS, parse_input_lemma
from giellaltlextools.lexc import scrapelemmas


class TestGtSpellTestRegression(unittest.TestCase):
    def test_parse_input_lemma_preserves_multiword(self):
        line = "Input: vuesiehtimmien gaavhtan          [INCORRECT]"
        self.assertEqual(parse_input_lemma(line), "vuesiehtimmien gaavhtan")

    def test_default_exclusions_drop_non_speller_use_tags(self):
        data = "\n".join(
            [
                "oklemma+N:oklemma N ;",
                "usemt+Use/MT:usemt N ;",
                "usemarg+Use/Marg:usemarg N ;",
                "usetts+Use/TTS:usetts N ;",
                "usepmatch+Use/PMatch:usepmatch N ;",
                "usegc+Use/GC:usegc N ;",
                "nospell+Use/-Spell:nospell N ;",
            ]
        )
        lemmas = scrapelemmas(io.StringIO(data), DEFAULT_EXCLUSIONS)
        self.assertIn("oklemma", lemmas)
        self.assertNotIn("usemt", lemmas)
        self.assertNotIn("usemarg", lemmas)
        self.assertNotIn("usetts", lemmas)
        self.assertNotIn("usepmatch", lemmas)
        self.assertNotIn("usegc", lemmas)
        self.assertNotIn("nospell", lemmas)


if __name__ == "__main__":
    unittest.main()
