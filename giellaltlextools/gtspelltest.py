#!/usr/bin/env python3
"""Lemma testing for GiellaLT spell-checkers and lexicons."""

import subprocess
import sys
import tempfile
from argparse import ArgumentParser

from .lexc import scrapelemmas


def main():
    """CLI for speller lemma testing."""
    argp = ArgumentParser()
    argp.add_argument("lexcfilenames", nargs="+",
                      help="read lemmas from the lexc files")
    argp.add_argument("-z", "--zhfst", type=str, dest="zhfstfilename",
                      help="ZHFST speller for analysing missing lemmas",
                      required=True)
    argp.add_argument("-D", "--runner", type=str, dest="runnerfilename",
                      help="external runner capable of handling zhfst",
                      required=True)
    argp.add_argument("-T", "--threshold", type=int,
                      help="required % proportion of succesful generations",
                      default=99)
    argp.add_argument("-d", "--debug", action="store_true", default=False,
                      help="prints debugging outputs")
    argp.add_argument("-v", "--verbose", action="store_true", default=False,
                      help="prints some outputs")
    argp.add_argument("-Z", "--acceptable-forms", type=open,
                      help="do not count oov if analysis contained in file")
    argp.add_argument("-X", "--exclude", action="append",
                      help="exclude lines matching regex")
    argp.add_argument("-Q", "--oov-limit", type=int, default=100_000,
                      help="stop trying after so many oovs")
    argp.add_argument("-B", "--time-out", type=int, default=60,
                      help="max time used to test lemmas")
    options = argp.parse_args()
    logfile = tempfile.NamedTemporaryFile(prefix="lemmaspell", suffix=".txt",
                                          delete=False, encoding="UTF-8",
                                          mode="w+")
    if "divvunspell" in options.runnerfilename:
        spellargs = [options.runnerfilename, "suggest", "--archive",
                     options.zhfstfilename]
    elif "hfst-ospell" in options.runnerfilename:
        spellargs = [options.runnerfilename, "-S", options.zhfstfilename]
    else:
        print(f"fail - unknown runner {options.runnerfilename}")
        sys.exit(1)
    skipforms = None
    if options.acceptable_forms:
        skipforms = [l.strip() for l in options.acceptable_forms.readlines()]
    lemmas = set()
    for lexcfilename in options.lexcfilenames:
        with open(lexcfilename, encoding="utf-8") as lexcfile:
            more = scrapelemmas(lexcfile, options.exclude, options.debug)
            for lemma in more:
                lemmas.add(lemma)
    lines = 0
    oovs = 0
    if options.verbose:
        print(f"collected {len(lemmas)} lemmas, sending...")
    lemmabytes = "\n".join(lemmas).encode("utf-8")
    try:
        results = subprocess.run(spellargs, input=lemmabytes,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 check=True, timeout=options.time_out)
    except subprocess.TimeoutExpired:
        print("Warning: lemma checking timed out")
        sys.exit(77)
    skipping = True
    if options.verbose:
        print("processing done.")
    for line in results.stdout.decode("utf-8").strip().split("\n"):
        if "Input:" in line:
            lemma = line.split()[1]
            if lemma in {"", "#", "#;"}:
                skipping = True
            elif skipforms and lemma in skipforms:
                skipping = True
            else:
                skipping = False
                lines += 1
        if skipping:
            continue
        if "[INCORRECT]" in line:
            oovs += 1
            if options.verbose:
                print(f"{lemma} is not accepted")
            print(f"{lemma}", file=logfile)
            print("\tfollowing suggestions:", file=logfile)
        else:
            if "Input:" not in line:
                print(f"\t{line}", file=logfile)
        if oovs >= options.oov_limit:
            print("too many fails, bailing to save time...")
            break
    if lines == 0:
        print(f"SKIP: could not find lemmas in {options.lexcfilenames}")
        sys.exit(77)
    coverage = (1.0 - (float(oovs) / float(lines))) * 100.0
    if options.verbose:
        print("Lemma statistics:")
        print(f"\t{len(lemmas)} lemmas")
        print(f"\t{coverage} % accepted")
    if coverage < options.threshold:
        print("FAIL: too many lemmas weren't generating!",
              f"{coverage} < {options.threshold}")
        print(f"see {logfile.name} for details ({oovs} ungenerated strings)")
        sys.exit(1)
    else:
        print(f"PASS: {len(lemmas)} lemmas {coverage} % accepted")
        if coverage < 100:
            print(f"see {logfile.name} for remaining lemmas")


if __name__ == "__main__":
    main()
