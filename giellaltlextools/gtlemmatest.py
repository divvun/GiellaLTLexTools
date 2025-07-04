#!/usr/bin/env python3
"""GiellaLT tests for lemma generation."""

import re
import sys
import tempfile
from argparse import ArgumentParser

from .hfst import load_hfst
from .lexc import scrapelemmas


def main():
    """CLI for GiellaLT lemma generation tests."""
    argp = ArgumentParser()
    argp.add_argument("-l", "--lexc", type=open, dest="lexcfile",
                      help="read lemmas from the lexc file",
                      required=True)
    argp.add_argument("-a", "--analyser", type=str, dest="analyserfilename",
                      help="FST analyser for analysing missing lemmas",
                      required=True)
    argp.add_argument("-g", "--generator", type=str, dest="generatorfilename",
                      help="FST generator file for generating the forms",
                      required=True)
    argp.add_argument("-t", "--tags", action="append",
                      help="tags that lemma form should have in generator",
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
    argp.add_argument("-Q", "--oov-limit", type=int, default=1000,
                      help="stop trying after so many oovs")
    options = argp.parse_args()
    logfile = tempfile.NamedTemporaryFile(prefix="paradigm", suffix=".txt",
                                          delete=False, encoding="UTF-8",
                                          mode="w+")
    generator = load_hfst(options.generatorfilename)
    analyser = load_hfst(options.analyserfilename)
    skipforms = None
    if options.acceptable_forms:
        skipforms = [l.strip() for l in options.acceptable_forms.readlines()]
    lemmas = scrapelemmas(options.lexcfile, options.exclude, options.debug)
    lines = 0
    oovs = 0
    for lemma in lemmas:
        if lemma in {"", "#", "#;"}:
            continue
        failed = True
        for tagstring in options.tags:
            generations = generator.lookup(lemma + tagstring,
                                           time_cutoff=0.1)
            if len(generations) == 0:
                if options.verbose:
                    print(f"{lemma}{tagstring} does not generate!")
            else:
                failed = False
        if skipforms and lemma in skipforms:
            continue
        lines += 1
        if failed:
            oovs += 1
            for tagstring in options.tags:
                print(f"{lemma}{tagstring}", file=logfile)
            analyses = analyser.lookup(lemma,
                                       time_cutoff=0.1)
            if len(analyses) > 0:
                print(f"\tN.B: {lemma} has following analyses", file=logfile)
                for analysis in analyses:
                    print(f"\t{analysis}", file=logfile)
            if oovs >= options.oov_limit:
                print("too many fails, bailing to save time...")
                break
    if lines == 0:
        print(f"SKIP: could not find lemmas in {options.lexcfile.name}")
        sys.exit(77)
    coverage = (1.0 - (float(oovs) / float(lines))) * 100.0
    if options.verbose:
        print("Lemma statistics:")
        print(f"\t{len(lemmas)} lemmas")
        print(f"\t{coverage} % success")
    if coverage < options.threshold:
        print("FAIL: too many lemmas weren't generating!",
              f"{coverage} < {options.threshold}")
        print(f"see {logfile.name} for details ({oovs} ungenerated strings)")
        sys.exit(1)


if __name__ == "__main__":
    main()
