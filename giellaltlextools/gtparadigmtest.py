#!/usr/bin/env python3
"""GiellaLT tests for paradigm generations."""

import sys
import tempfile
from argparse import ArgumentParser
from subprocess import Popen
from time import time

from . import __version__
from .hfstpope import load_hfst_pope
from .hfst import load_hfst
from .lexc import scrapelemmas


def main():
    """CLI for GiellaLT paradigm generation tests."""
    argp = ArgumentParser()
    argp.add_argument("-V", "--version", action="version",
                      version=f"%(prog)s {__version__}",
                      help="print version info")
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
                      help="required percentage of succesful generations",
                      default=99)
    argp.add_argument("-d", "--debug", action="store_true", default=False,
                      help="prints debugging outputs")
    argp.add_argument("-v", "--verbose", action="store_true", default=False,
                      help="prints some outputs")
    argp.add_argument("-B", "--time-out", type=int, default=60,
                      help="max time spend on lemmas")
    argp.add_argument("-Q", "--oov-limit", type=int, default=10_000,
                      help="stop trying after so many oovs")
    argp.add_argument("-X", "--acceptable-tags", action="append",
                      help="do not count oov if analyses contain these tags")
    argp.add_argument("-Z", "--acceptable-forms", type=open,
                      help="do not count oov if analysis contained in file")
    argp.add_argument("-E", "--editor", type=str,
                      help="open failures in EDITOR afterwards")
    argp.add_argument("-D", "--driver", choices=["subprocess", "pyhfst"],
                      default="subprocess",
                      help="select method of running hfstol files")
    options = argp.parse_args()
    logfile = tempfile.NamedTemporaryFile(prefix="gtparadigmtest", suffix=".txt",
                                          delete=False, encoding="UTF-8",
                                          mode="w+")
    if options.driver == "subprocess":
        generator = load_hfst_pope(options.generatorfilename)
    elif options.driver == "pyhfst":
        generator = load_hfst(options.generatorfilename)
    else:
        print(f"unusable driver {options.driver}")
        sys.exit(2)
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
    start = time()
    timedout = False
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
                    if oovs >= options.oov_limit:
                        print(f"FAILing fast after too many fails: {oovs}")
                        print("\nFINISHED PREMATURELY TOO MANY FAILS: ",
                              oovs, file=logfile)
                        print(f"see {logfile.name} for details")
                        if options.editor:
                            Popen([options.editor, logfile.name])
                        sys.exit(1)
            lines += 1
            forms += len(generations)
            if options.debug:
                print(f"{lemma}{paradigm}:")
                for g in generations:
                    print(f"\t{g}")
        now = time()
        if now - start > options.time_out:
            print(f"Bailing after timeout {now - start}")
            timedout = True
            break
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
        if options.editor:
            Popen([options.editor, logfile.name])
        sys.exit(1)
    elif timedout and oovs:
        print("FAIL: timed out and failures...")
        print(f"see {logfile.name} for details ({oovs} ungenerated strings)")
        if options.editor:
            Popen([options.editor, logfile.name])
        sys.exit(1)
    elif timedout:
        print("SKIP: timed out but found no errors")
        sys.exit(77)


if __name__ == "__main__":
    main()
