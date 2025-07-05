#!/usr/bin/env python3
"""GiellaLT tests for paradigm generations."""

import sys
import tempfile
from argparse import ArgumentParser

from .hfst import load_hfst
from .lexc import scrapelemmas


def main():
    """CLI for GiellaLT paradigm generation tests."""
    argp = ArgumentParser()
    argp.add_argument("-p", "--paradigm", type=open, dest="paradigmfile",
                      help="list of tagstrings making up the paradigm",
                      required=True)
    argp.add_argument("-l", "--lexc", type=open, dest="lexcfile",
                      help="read lemmas from the lexc file",
                      required=True)
    argp.add_argument("-g", "--generator", type=str, dest="generatorfilename",
                      help="FST generator file for generating the forms",
                      required=True)
    argp.add_argument("-T", "--threshold", type=int,
                      help="required % proportion of succesful generations",
                      default=99)
    argp.add_argument("-d", "--debug", action="store_true", default=False,
                      help="prints debugging outputs")
    argp.add_argument("-v", "--verbose", action="store_true", default=False,
                      help="prints some outputs")
    argp.add_argument("-X", "--acceptable-tags", action="append",
                      help="do not count oov if analyses contain these tags")
    argp.add_argument("-Z", "--acceptable-forms", type=open,
                      help="do not count oov if analysis contained in file")
    options = argp.parse_args()
    logfile = tempfile.NamedTemporaryFile(prefix="paradigm", suffix=".txt",
                                          delete=False, encoding="UTF-8",
                                          mode="w+")
    generator = load_hfst(options.generatorfilename)
    paradigms = [l.strip() for l in options.paradigmfile.readlines() if
                 l.strip() != ""]
    skipforms = None
    if options.acceptable_forms:
        skipforms = [l.strip() for l in options.acceptable_forms.readlines()]
    skiptags = options.acceptable_tags
    lemmas = scrapelemmas(options.lexcfile, None, options.debug)
    lines = 0
    forms = 0
    oovs = 0
    for lemma in lemmas:
        for paradigm in paradigms:
            generations = generator.lookup(lemma + paradigm)
            if len(generations) == 0:
                ignoring = False
                if skiptags:
                    for skip in skiptags:
                        if skip in paradigm.split("+"):
                            ignoring = True
                            break
                if skipforms:
                    if lemma + paradigm in skipforms:
                        ignoring = True
                if not ignoring:
                    if options.verbose:
                        print(f"{lemma}{paradigm} does not generate!")
                    print(f"{lemma}{paradigm}", file=logfile)
                    oovs += 1
            lines += 1
            forms += len(generations)
            if options.debug:
                print(f"{lemma}{paradigm}:")
                for g in generations:
                    print(f"\t{g}")
    if lines == 0:
        print(f"SKIP: could not find lemmas in {options.lexcfile.name}")
        sys.exit(77)
    coverage = (1.0 - (float(oovs) / float(lines))) * 100.0
    if options.verbose:
        print("Generation statistics:")
        print(f"\t{len(lemmas)} lemmas × {len(paradigms)} paradigm slots")
        print(f"\t(should be minimum {len(lemmas)*len(paradigms)} forms then)")
        print(f"\t{forms} generated, {coverage} % success")
    if coverage < options.threshold:
        print("FAIL: too many lemmas weren't generating!",
              f"{coverage} < {options.threshold}")
        print(f"see {logfile.name} for details ({oovs} ungenerated strings)")
        sys.exit(1)


if __name__ == "__main__":
    main()
