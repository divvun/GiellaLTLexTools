#!/usr/bin/env python3
"""GiellaLT tests for lemma generation."""

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
    """CLI for GiellaLT lemma generation tests."""
    argp = ArgumentParser()
    argp.add_argument("-V", "--version", action="version",
                      version=f"%(prog)s {__version__}",
                      help="print version info")
    argp.add_argument("-T", "--threshold", type=int,
                      help="required percentage of succesful generations",
                      default=100)
    argp.add_argument("-d", "--debug", action="store_true", default=False,
                      help="prints debugging outputs")
    argp.add_argument("-v", "--verbose", action="store_true", default=False,
                      help="prints some outputs")
    argp.add_argument("-Q", "--oov-limit", type=int, default=10_000,
                      help="stop trying after so many oovs")
    argp.add_argument("-B", "--time-out", type=int, default=60,
                      help="max time to use with lemmas")
    argp.add_argument("-E", "--editor", type=str, metavar="EDITOR",
                      help="open failures in EDITOR afterwards")
    argp.add_argument("-D", "--driver", choices=["subprocess", "pyhfst"],
                      default="subprocess",
                      help="use subprocess instead of pyhfst for hfst lookups")
    argp.add_argument("-c", "--config", type=open, metavar="CONFIG",
                      help="read json options from CONFIG", required=True)
    argp.add_argument("-P", "--pos", type=str, metavar="POS",
                      help="read configs from POS section", required=True)
    argp.add_argument("-L", "--log-file", type=FileType("w"),
                      dest="logfile", metavar="LOGFILE",
                      help="save permanent markdown log in LOGFILE")
    options = argp.parse_args()
    if options.logfile:
        dostuff(options, options.logfile)
    else:
        with tempfile.NamedTemporaryFile(prefix="gtlemmatest", suffix=".md",
                                         delete=False, encoding="UTF-8",
                                         mode="w+") as logfile:
            dostuff(options, logfile)
    print(colored("SUCCESS", "green"))


def dostuff(options: Namespace, logfile: TextIO):
    """Run lemma generation tests."""
    configuration = json.load(options.config)
    lexcfilename = configuration[options.pos]["lexcfile"]
    print(f"# Lemma-tests for *{options.pos}* in `{basename(lexcfilename)}`",
          file=logfile)
    print(file=logfile)
    print(f"Settings used:\n\n```json\n{configuration}\n```", file=logfile)
    skiplemmas = None
    if "acceptable_lemmas_file" in configuration[options.pos]:
        with open(configuration[options.pos]["acceptable_lemmas_file"],
                  encoding="UTF-8") as lemmafile:
            skiplemmas = [l.strip() for l in lemmafile.readlines()]
    start = time()
    if options.driver == "subprocess":
        generator = load_hfst_pope(configuration["generator"])
        analyser = load_hfst_pope(configuration["analyser"])
    elif options.driver == "pyhfst":
        generator = load_hfst(configuration["generator"])
        analyser = load_hfst(configuration["analyser"])
    else:
        print(f"bad driver {options.driver}")
        sys.exit(2)
    end = time()
    if options.verbose:
        print(f"used {end-start} times for FSA / subprocess startup")
    start = time()
    with open(lexcfilename, encoding="UTF-8") as lexcfile:
        lemmas = scrapelemmas(lexcfile,
                          configuration[options.pos]["exclusions"],
                          options.debug)
    end = time()
    if options.verbose:
        print(f"used {end-start} times for lemma scraping")
    lines = 0
    oovs = 0
    misses = 0
    start = time()
    timedout = False
    for lemma in lemmas:
        if lemma in {"", "#", "#;"}:
            continue
        if skiplemmas and lemma in skiplemmas:
            continue
        empty = True
        matched = False
        mismatches = set()
        ungenerated = set()
        for tagstring in configuration[options.pos]["lemmatags"]:
            if options.verbose:
                print(f"trying {lemma}{tagstring}...")
            generations = generator.lookup(lemma + tagstring)
            if options.verbose:
                print(f"got {len(generations)}")
            if len(generations) == 0:
                ungenerated.add(f"* `{lemma}{tagstring}` does not generate!")
            else:
                empty = False
                for generation in generations:
                    if generation[0] == lemma:
                        matched = True
                    else:
                        mismatches.add(f"* `{lemma}{tagstring}` => {generation}")
        lines += 1
        if empty or not matched:
            print(f"\n**{lemma}** failures:\n", file=logfile)
        if empty:
            oovs += 1
            for degenerate in ungenerated:
                print(degenerate, file=logfile)
        if not matched:
            misses += 1
            for mismatch in mismatches:
                print(mismatch, file=logfile)
        if empty or not matched:
            analyses = analyser.lookup(lemma)
            if len(analyses) > 0:
                print(f"* `{lemma}` has following analyses:", file=logfile)
                uniques = set()
                for analysis in analyses:
                    uniques.add(analysis[0])
                for analysis in uniques:
                    print(f"  * {analysis}", file=logfile)
                    if options.verbose:
                        print(f"\t{analysis}")
            else:
                print(f"\t{lemma} has no analyses either", file=logfile)
        if oovs >= options.oov_limit:
            print("too many fails, bailing to save time...")
            print("**FINISHED PREMATURELY HERE DUE TO too many errors**:",
                  oovs, file=logfile)
            break
        now = time()
        if now - start > options.time_out:
            print(f"bailing after timeout: {now - start}")
            print("**FINISHED PREMATURELY HERE DUE TO TIMEOUT**:",
                  options.time_out, file=logfile)
            timedout = True
            break
    end = time()
    if lines == 0:
        print(colored("SKIP:", "cyan"),
              f"could not find lemmas in {lexcfilename}")
        sys.exit(77)
    failures = oovs + misses
    coverage = (1.0 - (float(failures) / float(lines))) * 100.0
    if options.verbose:
        print(f"used {end-start} times for generating")
        print("Lemma statistics:")
        print(f"\t{len(lemmas)} lemmas")
        print(f"\t{coverage} % success")
    if coverage < options.threshold:
        print(colored("FAIL:", "red"),
              f"{oovs} ungenerated strings, {misses} wrong lemmas",
              f"({coverage} < {options.threshold})")
        print("open", colored(lexcfilename, "cyan"), "to fix")
        print("see", colored(logfile.name, "magenta"), "for details")
        if options.editor:
            print(f"Running: {options.editor} {logfile.name}")
            Popen([options.editor, logfile.name])
        sys.exit(1)
    else:
        if timedout and failures > 0:
            print(colored("FAIL:", "red"), "timed out with ungenerated lemmas")
            print(f"{oovs} ungenerated strings, {mismatches} wrong lemmas")
            print(f"see {logfile.name} for details")
            if options.editor:
                print(f"Running: {options.editor} {logfile.name}")
                Popen([options.editor, logfile.name])
            sys.exit(1)
        elif timedout:
            print(colored("SKIP:", "cyan"),
                  "timed out but didn't find  problems..")
            sys.exit(77)
        elif failures > 0:
            print(colored("SUCCESS:", "green"),
                  f"{oovs} ungenerated strings, {mismatches} wrong lemmas",
                  f"(accepted by -T: {coverage} >= {options.threshold})")
            if options.editor:
                print(f"Running: {options.editor} {logfile.name}")
                Popen([options.editor, logfile.name])
                sys.exit(0)
    if failures > 0:
        print(colored("SUCCESS:", "green"),
              f"{oovs} ungenerated strings, {mismatches} wrong lemmas",
              f"{coverage} >= {options.threshold})"
              f"(accepted by -T: {coverage} >= {options.threshold})")
        if options.editor:
            print(f"Running: {options.editor} {logfile.name}")
            Popen([options.editor, logfile.name])
            sys.exit(0)


if __name__ == "__main__":
    main()
