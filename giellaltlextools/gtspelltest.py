#!/usr/bin/env python3
"""Lemma testing for GiellaLT spell-checkers and lexicons."""

import json
import re
import subprocess
import sys
import tempfile
from argparse import ArgumentParser, FileType, Namespace
from os.path import basename
from subprocess import Popen
from typing import TextIO

from termcolor import colored, cprint

from . import __version__
from .lexc import scrapelemmas

DEFAULT_EXCLUSIONS = [
    r"\+Use/-Spell",
    r"\+Use/MT",
    r"\+Use/Marg",
    r"\+Use/TTS",
    r"\+Use/PMatch",
    r"\+Use/GC",
    r"\+CmpNP/Pref",
    r"\+CmpNP/Suff",
    r"\+CmpNP/Only",
]

def prettyprint_json(config):
    """Pretty-print a JSON config."""
    prettyfiles = []
    for lexcfilename in config["lexcfiles"]:
        prettyfiles.append(".../" + basename(lexcfilename))
    config["lexcfiles"] = prettyfiles
    config["zhfstfile"] = ".../" + basename(config["zhfstfile"])
    return json.dumps(config, indent=4, sort_keys=True)


def parse_input_lemma(line: str) -> str:
    """Extract full input lemma from a divvunspell/hfst-ospell output line."""
    match = re.match(r"^Input:\s*(.*?)\s+\[[^\]]+\]\s*$", line)
    if match:
        return match.group(1)
    if "Input:" in line:
        return line.split("Input:", maxsplit=1)[1].strip()
    return ""


def main():
    """CLI for speller lemma testing."""
    argp = ArgumentParser()
    argp.add_argument("-V", "--version", action="version",
                      version=f"%(prog)s {__version__}",
                      help="print version info")
    argp.add_argument("-D", "--runner", type=str, dest="runnerfilename",
                      help="external runner capable of handling zhfst",
                      required=True)
    argp.add_argument("-T", "--threshold", type=int,
                      help="required percentage of succesful generations",
                      default=100)
    argp.add_argument("-d", "--debug", action="store_true", default=False,
                      help="prints debugging outputs")
    argp.add_argument("-v", "--verbose", action="store_true", default=False,
                      help="prints some outputs")
    argp.add_argument("-Q", "--oov-limit", type=int, default=100_000,
                      help="stop trying after so many oovs")
    argp.add_argument("-B", "--time-out", type=int, default=60,
                      help="max time used to test lemmas")
    argp.add_argument("-E", "--editor", type=str,
                      help="open failures in EDITOR afterwards")
    argp.add_argument("-c", "--config", type=open, metavar="CONFIGFILE",
                      help="read configuration from CONFIGFILE", required=True)
    argp.add_argument("-L", "--logfile", type=FileType("w"), metavar="LOGFILE",
                      help="save permanent markdown log in LOGFILE")
    options = argp.parse_args()
    if options.logfile:
        dostuff(options, options.logfile)
    else:
        with tempfile.NamedTemporaryFile(prefix="gtlemmaspell", suffix=".md",
                                         delete=False, encoding="UTF-8",
                                         mode="w+") as logfile:
            dostuff(options, logfile)


def dostuff(options: Namespace, logfile: TextIO):
    """Run spell-checking tests for lemmas."""
    configuration = json.load(options.config)
    if "divvunspell" in options.runnerfilename:
        spellargs = [options.runnerfilename, "suggest", "--archive",
                     configuration["zhfstfile"]]
    elif "hfst-ospell" in options.runnerfilename:
        spellargs = [options.runnerfilename, "-S", configuration["zhfstfile"]]
    else:
        print(colored("fail", "red"),
              f"- unknown runner {options.runnerfilename}")
        sys.exit(1)
    skipforms = None
    if "acceptable_form_file" in configuration:
        with open(configuration["acceptable_form_file"],
                  encoding="utf-8") as acceptable_forms:
            skipforms = [l.strip() for l in acceptable_forms.readlines()]
    exclusions = DEFAULT_EXCLUSIONS.copy()
    if "exclusions" in configuration:
        exclusions.extend(configuration["exclusions"])
    lemmas = set()
    for lexcfilename in configuration["lexcfiles"]:
        with open(lexcfilename, encoding="utf-8") as lexcfile:
            more = scrapelemmas(lexcfile, exclusions, options.debug)
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
        print(colored("Warning:", "yellow"), "lemma checking timed out")
        sys.exit(77)
    skipping = True
    if options.verbose:
        print("processing done.")
    print("# Results for lemmatesting spell-checker\n", file=logfile)
    for line in results.stdout.decode("utf-8").strip().split("\n"):
        if "Input:" in line:
            lemma = parse_input_lemma(line)
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
            print(f"\n**{lemma}** is missing. ", file=logfile)
            print("following suggestions:", file=logfile)
        else:
            if "Input:" not in line:
                print(f"* {line}", file=logfile)
        if oovs >= options.oov_limit:
            print("too many fails, bailing to save time...")
            break
    if lines == 0:
        print(colored("SKIP:", "cyan"),
              f"could not find lemmas in {configuration["lexcfiles"]}")
        sys.exit(77)
    coverage = (1.0 - (float(oovs) / float(lines))) * 100.0
    if options.verbose:
        print("Lemma statistics:")
        print(f"\t{len(lemmas)} lemmas")
        print(f"\t{coverage} % accepted")
    print("\n## Lemma statistics:\n", file=logfile)
    print(f"* {len(lemmas)} lemmas", file=logfile)
    print(f"* {coverage} % accepted", file=logfile)
    prettyconfig = prettyprint_json(configuration)
    print(f"\n## Configuration:\n\n```json\n{prettyconfig}\n```", file=logfile)
    if coverage < options.threshold:
        print(colored("FAIL:", "red"), f"{oovs} lemmas failed!",
              f"({coverage} % < {options.threshold} %)")
        print("fix lemmas in follwoing files please:",
              colored(configuration["lexcfiles"], "cyan"))
        print("see", colored(logfile.name, "magenta"), "for details")
        if options.editor:
            print(f"Running {options.editor} {logfile.name}...")
            Popen([options.editor, logfile.name])
        sys.exit(1)
    else:
        print(colored("PASS:", "green"),
              f"{len(lemmas)} lemmas {coverage} % accepted")
        if coverage < 100:
            print("fix lemmas in follwoing files please:",
                  colored(configuration["lexcfiles"], "cyan"))
            print("see", colored(logfile.name, "magenta"), "for details")


if __name__ == "__main__":
    main()
