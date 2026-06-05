#!/usr/bin/env python3
"""GiellaLT tests for paradigm generations."""

import json
import sys
import tempfile
from argparse import ArgumentParser, FileType, Namespace
from os.path import basename
from subprocess import Popen
from time import time
from typing import TextIO

from termcolor import colored, cprint

from . import __version__
from .hfst import load_hfst
from .hfstpope import load_hfst_pope
from .lexc import scrapelemmas


def main():
    """CLI for GiellaLT paradigm generation tests."""
    argp = ArgumentParser()
    argp.add_argument("-V", "--version", action="version",
                      version=f"%(prog)s {__version__}",
                      help="print version info")
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
    argp.add_argument("-E", "--editor", type=str,
                      help="open failures in EDITOR afterwards")
    argp.add_argument("-D", "--driver", choices=["subprocess", "pyhfst"],
                      default="subprocess",
                      help="select method of running hfstol files")
    argp.add_argument("-c", "--config", type=open, metavar="CONFIG",
                      help="read json options from CONFIG", required=True)
    argp.add_argument("-P", "--pos", type=str, metavar="POS",
                      help="read config from POS section", required=True)
    argp.add_argument("-L", "--log-file", type=FileType("w"),
                      dest="logfile", metavar="LOGFILE",
                      help="save permanent markdown log in LOGFILE")
    options = argp.parse_args()
    if options.logfile:
        dostuff(options, options.logfile)
    else:
        with tempfile.NamedTemporaryFile(prefix="gtparadigmtest", suffix=".txt",
                                         delete=False, encoding="UTF-8",
                                         mode="w+") as logfile:
            dostuff(options, logfile)
    print(colored("SUCCESS", "green"))


def dostuff(options: Namespace, logfile: TextIO):
    """Run paradigm generation tests."""
    configuration = json.load(options.config)
    lexcfilename = configuration[options.pos]["lexcfile"]
    print(f"# Paradigm tests for *{options.pos}* in "
          f"...`{basename(lexcfilename)}`\n", file=logfile)
    if options.driver == "subprocess":
        generator = load_hfst_pope(configuration["generator"])
    elif options.driver == "pyhfst":
        generator = load_hfst(configuration["generator"])
    else:
        print(f"unusable driver {options.driver}")
        sys.exit(2)
    if "paradigmfile" in configuration[options.pos]:
        with open(configuration[options.pos]["paradigmfile"], encoding="utf-8") as \
                  paradigmfile:
            paradigms = [l.strip() for l in paradigmfile.readlines() if
                         l.strip() != ""]
    else:
        print(colored("skip:", "cyan"),
              f"paradigmfile missing for {options.pos}",
              f"in {options.config.name}")
        sys.exit(77)
    skipforms = None
    if "exceptionfile" in configuration[options.pos]:
        with open(configuration[options.pos]["exceptionfile"], encoding="utf-8") as \
                  exceptionfile:
            skipforms = [l.strip() for l in exceptionfile.readlines()]
    skiptags = None
    if "skiptags" in configuration[options.pos]:
        skiptags = configuration[options.pos]
    else:
        skiptags =None
    if "exclusions" in configuration[options.pos]:
        exclusions = configuration[options.pos]["exclusions"]
    else:
        exclusions = None
    with open(lexcfilename, encoding="utf-8") as lexcfile:
        lemmas = scrapelemmas(lexcfile, exclusions, options.debug)
    lines = 0
    forms = 0
    oovs = 0
    start = time()
    timedout = False
    for lemma in lemmas:
        misses: list[str] = []
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
                    misses.append(f"  * `{lemma}{paradigm}` ?")
                    oovs += 1
                    if oovs >= options.oov_limit:
                        print(f"FAILing fast after too many fails: {oovs}")
                        print("**Finished prematurely because too many fails**:",
                              oovs, file=logfile)
                        for miss in misses:
                            print(miss, file=logfile)
                        print(f"see {logfile.name} for details")
                        if options.editor:
                            print(f"running {options.editor} {logfile.name}:")
                            Popen([options.editor, logfile.name])
                        sys.exit(1)
            lines += 1
            forms += len(generations)
            if options.debug:
                print(f"{lemma}{paradigm}:")
                for g in generations:
                    print(f"\t{g}")
        if misses:
            print(f"* **{lemma}** failures:", file=logfile)
            for miss in misses:
                print(miss, file=logfile)
        now = time()
        if now - start > options.time_out:
            print(f"Bailing after timeout {now - start}")
            print("**Finished prematurely because time-out:**", file=logfile)
            timedout = True
            break
    if lines == 0:
        print(f"SKIP: could not find lemmas in {lexcfilename}")
        sys.exit(77)
    coverage = (1.0 - (float(oovs) / float(lines))) * 100.0
    if options.verbose:
        print("Generation statistics:")
        print(f"\t{len(lemmas)} lemmas × {len(paradigms)} paradigm slots")
        print(f"\t(should be minimum {len(lemmas)*len(paradigms)} forms then)")
        print(f"\t{forms} generated, {coverage} % success")
    print("\n## Paradigm statistics", file=logfile)
    print(f"* {len(lemmas)} lemmas × {len(paradigms)} paradigm slots")
    print(f"* (should be minimum {len(lemmas)*len(paradigms)} forms then)")
    print(f"* {forms} generated, {coverage} % success")
    if coverage < options.threshold:
        print(colored("FAIL:", "red"), "too many lemmas weren't generating!",
              f"{coverage} < {options.threshold}")
        print(f"see {logfile.name} for details ({oovs} ungenerated strings)")
        if options.editor:
            Popen([options.editor, logfile.name])
        sys.exit(1)
    elif timedout and oovs:
        print(colored("FAIL:", "red"), "timed out and failures...")
        print(f"see {logfile.name} for details ({oovs} ungenerated strings)")
        if options.editor:
            Popen([options.editor, logfile.name])
        sys.exit(1)
    elif timedout:
        print("SKIP: timed out but found no errors")
        sys.exit(77)


if __name__ == "__main__":
    main()
