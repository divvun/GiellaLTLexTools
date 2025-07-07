#!/usr/bin/env python3
"""Functions for handling lexc data."""

import re
from typing import IO

GLOBAL_EXCLUSIONS = ["CmpN/Only", "ShCmp", "Cmp/SplitR",
                     " Rreal ", " R ", " RNoun ", "NOT-TO-LEMMATEST",
                     "Use/Spell-", "SpellNoSugg", "\\+Pref"]


def hidelexcescapes(s: str) -> str:
    """Encode lexc special characters differently.

    This function is designed to process a line or a block of lexc data
    including a single lexeme entry. But it'll work for any lexc snippet
    usually."""
    s = s.replace("%!", "§EXCLAMATIONMARK§")
    s = s.replace("%:", "§COLON§")
    s = s.replace("%<", "§LESSTHAN§")
    s = s.replace("% ", "§SPACE§")
    if "<" in s and ">" in s:
        s = re.sub("<.*>", "§REGEX§", s)
    if "\"" in s:
        s = s.replace("%\"", "§QUOTATIONMARK§")
        if "\"" in s:
            # archaic translation comment
            s = re.sub("\".*\"", "", s)
    return s


def unhidelexcescapes(s: str, unescape=True) -> str:
    """Restore encoded lexc special characters.

    Uses % escaping if unescape is False, otherwise characters are restored to
    actual surface form.
    """
    if unescape:
        s = s.replace("§EXCLAMATIONMARK§", "!")
        s = s.replace("§COLON§", ":")
        s = s.replace("§LESSTHAN§", "<")
        s = s.replace("§SPACE§", " ")
        s = s.replace("§QUOTATIONMARK§", "\"")
    else:
        s = s.replace("§EXCLAMATIONMARK§", "%!")
        s = s.replace("§COLON§", ":")
        s = s.replace("§LESSTHAN§", "<")
        s = s.replace("§SPACE§", " ")
        s = s.replace("§QUOTATIONMARK§", "%\"")
    return s


def killflagdiacritics(s: str) -> str:
    """Remove flag diacritics from the string."""
    if "@" in s:
        s = re.sub("@[CRDPNU].[^@]*@", "", s)
    return s

def scrapelemmas(f: IO[str], exclusions: list[str], debug=False) -> set[str]:
    """Gets all lemmas from a lexc file."""
    lemmas = set()
    for lexcline in f:
        if not lexcline or lexcline.strip() == "":
            continue
        excluded = False
        if exclusions:
            for exclusion in exclusions:
                if re.search(exclusion, lexcline):
                    excluded = True
            if excluded:
                continue
        for exclusion in GLOBAL_EXCLUSIONS:
            if re.search(exclusion, lexcline):
                excluded = True
        if excluded:
            continue
        # preproc
        lexcline = hidelexcescapes(lexcline)
        if "!" in lexcline:
            lexcline = lexcline.split("!")[0]
        lexcline = lexcline.strip()
        lexcline = killflagdiacritics(lexcline)
        # see stuff
        if lexcline.startswith("LEXICON "):
            continue
        elif not lexcline or lexcline == "":
            continue
        if ";" not in lexcline:
            continue
        if "+Err" in lexcline:
            continue
        if len(lexcline.split()) <= 2:
            continue
        if ":" in lexcline:
            analysis = unhidelexcescapes(lexcline.split(":")[0])
            lemma = analysis.split("+")[0]
            if debug:
                print(lemma)
            lemmas.add(lemma)
        else:
            idstringy = unhidelexcescapes(lexcline.split()[0])
            lemma = idstringy.split("+")[0]
            if debug:
                print(lemma)
            lemmas.add(lemma)
    return lemmas


if __name__ == "__main__":
    pass
