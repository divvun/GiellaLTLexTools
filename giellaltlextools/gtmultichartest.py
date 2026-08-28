#!/usr/bin/env python3
"""GiellaLT tests for multichars in lexc."""

import json
import re
import sys
import tempfile
from argparse import ArgumentParser, FileType, Namespace
from os.path import basename, dirname
from subprocess import Popen
from time import time
from typing import TextIO

from termcolor import colored

from . import __version__
from .jsonconfig import prettyprint_json, prettyprint_lexcfilename

PLUSSUFFIXTAGRE = r"\+[A-Za-z0-9_-][^+@#]*"
PREFIXPLUSTAGRE = r"[^+@#]*[A-Za-z0-9_-]\+"
ATFLAGATRE = r"@[^@]+@"

def main():
    """CLI for GiellaLT lemma generation tests."""
    argp = ArgumentParser()
    argp.add_argument("-V", "--version", action="version",
                      version=f"%(prog)s {__version__}",
                      help="print version info")
    argp.add_argument("-d", "--debug", action="store_true", default=False,
                      help="prints debugging outputs")
    argp.add_argument("-v", "--verbose", action="store_true", default=False,
                      help="prints some outputs")
    argp.add_argument("-c", "--config", type=open, metavar="CONFIG",
                      help="read json options from config", required=True)
    argp.add_argument("-L", "--log-file", type=FileType("w"),
                      dest="logfile", metavar="LOGFILE",
                      help="save peramanent markdown log in LOGFILE")
    argp.add_argument("-E", "--editor", type=str, metavar="EDITOR",
                      help="open failures in EDITOR afterwards")
    options = argp.parse_args()
    if options.logfile:
        dostuff(options, options.logfile)
    else:
        with tempfile.NamedTemporaryFile(prefix="gtmultichartest",
                                         suffix=".md",
                                         delete=False, encoding="UTF-8",
                                         mode="w+") as logfile:
            dostuff(options, logfile)
    print(colored("SUCCESS", "green"))



def read_multichar_symbols(rootlexc: TextIO, options: Namespace,
                           logfile: TextIO, failcount: int) -> set[str]:
    """Read multichar symbols.

    rootlexc is read onlyt up until the end of Multichar_Symbols and is left
    ready to be continued for rest of the testing.
    """
    if options.verbose:
        print("reading Multichar_Symbols in",
              colored(rootlexc.name, "magenta"))
    declaredmultichars: set[str] = set()
    lines = 0
    inmultichars = False
    rootlexcname = prettyprint_lexcfilename(rootlexc.name)
    for line in rootlexc:
        lines += 1
        if not inmultichars:
            if line.startswith("Multichar_Symbols"):
                inmultichars = True
                rest = line[len("Multichar_Symbols") + 1:].strip()
                if "!" in rest:
                    rest = rest.split("!")[0].strip()
                if rest != "":
                    print(colored("FAIL: ", "red"),
                          f"trailing rubbish after multichar syms: {rest}")
                    print(f"1. trailing rubbish *{rest}* on multichars line:"
                          f"**{rootlexcname}.{lines}**: `{line}`",
                          file=logfile)
                    failcount += 1
                print(f"## `Multichar_Symbols` in `{rootlexcname}`\n")
            elif line.startswith("Alphabets"):
                inmultichars = True
                rest = line[len("Alphabets") + 1:].strip()
                if "!" in rest:
                    rest = rest.split("!")[0].strip()
                if rest != "":
                    print(colored("FAIL: ", "red"),
                          f"trailing rubbish after alphabets: {rest}")
                    print(f"* trailing rubbish *{rest}* on alphabets line:"
                          f"**{rootlexcname}.{lines}**: `{line}`",
                          file=logfile)
                    failcount += 1
                print(f"## `Alphabets` in `{rootlexcname}`\n", file=logfile)
            elif line.startswith("LEXICON"):
                print(colored("FAIL: ", "red"),
                      f"found lexicons before multichars: {line.strip()}")
                print("1. lexicon before multichars: "
                      f"**{rootlexcname}.{lines}**: `{line}`", file=logfile)
                failcount += 1
            else:
                cleaned = line.split("!")[0].strip()
                if cleaned != "":
                    print(colored("FAIL:", "red"),
                          f"stuff before Multichars? {cleaned}")
                    print(f"stuff before multichar declaration {cleaned} "
                          f"**{rootlexcname}.{lines}**: `{line}`", file=logfile)
        else:  # inmultichars
            if line.startswith("LEXICON "):
                inmultichars = False
                if options.verbose:
                    print("Found following alphabets:\n",
                          ", ".join(declaredmultichars))
                    print("Reading lexicons now...")
                break
            if "!" in line:
                line = line.replace("%!", "§EXCLAMATION§")
                line = line.split("!")[0]
                line = line.replace("§EXCLAMATION§", "%!")
            line = line.replace("% ", "§SPACE§")
            for multichar in line.split():
                multichar = multichar.replace("§SPACE§", "% ")
                declaredmultichars.add(multichar)
    print(f"* {len(declaredmultichars)} declarations found "
          "(details in footer).\n", file=logfile)
    return declaredmultichars


def check_multichar_symbols(lexcfile: TextIO, declaredmultichars: set[str],
                            options: Namespace, logfile: TextIO) -> int:
    """Check for undeclared multichars in lexc entries in lexcfile."""
    if options.verbose:
        print("testing", colored(lexcfile.name, "magenta"),
              "for potential missing +tags, tags+ and",
              "@X.FLAG.DIACRITICS@")
    failcount = 0
    plussuffixtags = False
    prefixplustags = False
    atflagattags = False
    lexcfilename = prettyprint_lexcfilename(lexcfile.name)
    print(f"## Lexc entries in `{lexcfilename}`\n", file=logfile)
    for multichar in declaredmultichars:
        if multichar.startswith("+") and len(multichar) > 1:
            plussuffixtags = True
        if multichar.endswith("+") and len(multichar) > 1:
            prefixplustags = True
        if multichar.startswith("@") and multichar.endswith("@") and \
                len(multichar) > 1:
            atflagattags = True
    lines = 0
    for line in lexcfile:
        lines += 1
        if ";" in line:
            # for some reason split is confused by tabs and spaces mixed
            line = line.replace("\t", "    ")
            if "!" in line:
                line = line.replace("%!", "§EXCLAMATION§")
                line = line.split("!")[0]
                line = line.replace("§EXCLAMATION§", "%!")
            if "\"" in line:
                line = line.replace("%\"", "§QUOTATION§")
                line = re.sub(" \"[^\"]*\"", "", line)
                line = line.replace("§QUOTATION§", "\"")
            if "<" in line:
                line = line.replace("%<", "§LESSTHAN§")
                line = line.replace("%>", "§MORETHAN§")
                line = re.sub("<[^>]*>", "§REGEX§", line)
                if not "§REGEX§" in line:
                    line = re.sub("<.*", "§<MULTILINEREGEX§", line)
                line = line.replace("§LESSTHAN§", "%<")
                line = line.replace("§MORETHAN§", "%>")
            elif ">" in line:
                line = line.replace("%>", "§MORETHAN§")
                if ">" in line:
                    line = re.sub("^[^>]*>", "§MULTILINEREGEX>§", line)
                line = line.replace("§MORETHAN§", "%>")
            line = line.replace("%;", "§SEMICOLON§")
            if line.count(";") > 1:
                print(colored("FAIL: ", "red"),
                      f"too many semicolons on line {lines}:\n",
                      colored(line, "cyan"))
                print("1. too many semicolons",
                      f"**{lexcfilename}.{lines}**: `{line.strip()}`",
                      file=logfile)
                failcount += 1
                continue
            line = line.replace("§SEMICOLON§", "%;")
            if "% " in line:
                line = line.replace("% ", "§SPACE§")
            pairstring = None
            fields = line.split()
            for i, field in enumerate(fields):
                if field == ";":
                    if i >= 1:
                        _ = fields[i-1]
                    if i >= 2:
                        pairstring = fields[i-2]
                    if i >= 3:
                        if line.startswith("LEXICON "):
                            print(colored("FAIL:", "red"),
                                  "entries on LEXICON line is not "
                                  "supported:\n",
                                  colored({line}, "cyan"))
                            print("1. entries on LEXICON line",
                                  f"**{lexcfilename}.{lines}**:",
                                  f"`{line.strip()}`",
                                  file=logfile)
                            failcount += 1
                        else:
                            print(colored("FAIL:", "red"),
                                  "too many spaces? parsing:\n",
                                  colored(line, "cyan"))
                            print("1. too many spaces on line:"
                                  f"**{lexcfilename}.{lines}**:",
                                  f"`{line.strip()}`",
                                  file=logfile)
                            failcount += 1
            if pairstring:
                if ":" in pairstring:
                    deep = pairstring.split(":")[0]
                else:
                    deep = pairstring
                sussufix = []
                susprefix = []
                for tag in re.findall(PLUSSUFFIXTAGRE, deep):
                    if tag not in declaredmultichars:
                        if not tag[-1].isalpha() and \
                                tag[:-1] in declaredmultichars:
                            continue
                        sussufix.append([tag])
                for tag in re.findall(PREFIXPLUSTAGRE, deep):
                    if tag not in declaredmultichars:
                        susprefix.append([tag])
                if sussufix and plussuffixtags:
                    if not prefixplustags:
                        print(colored("FAIL:", "red"),
                              f"{sussufix} seem(s) like a multichar "
                              "suffix tag but is missing from the "
                              "Multichar_Symbols section "
                              f"on line {lines}:\n",
                              colored(line, "cyan"))
                        print(f"1. `{sussufix}` seems like multichars "
                              "suffix tag missing from declarations, in: "
                              f"**{lexcfilename}.{lines}**: `{line.strip()}`",
                              file=logfile)
                        failcount += 1
                    elif susprefix:
                        print(colored("FAIL:", "red"),
                              f"{sussufix} or {susprefix} seem like "
                              "potential multichars (suffixes or prefixes?)"
                              " but are missing from "
                              "Multichar_Symbols section "
                              f"on line {lines}:\n",
                              colored(line, "cyan"))
                        print(f"1. `{sussufix}` or `{susprefix} seem like "
                              "multichars tag missing from declarations"
                              "(couldn't determine if prefix or suffix), in: "
                              f"**{lexcfilename}.{lines}**: `{line.strip()}`",
                              file=logfile)
                        failcount += 1
                elif susprefix and prefixplustags:
                    if not plussuffixtags:
                        print(colored("FAIL:", "red"),
                              f"{susprefix} seem(s) like a multichar "
                              "prefix tag but is missing from the "
                              "Multichar_Symbols section "
                              f"on line {lines}:\n",
                              colored(line, "cyan"))
                        print(f"1. `{susprefix}` seems like multichars "
                              "prefix tag missing from declarations, in:"
                              f"**{lexcfilename}.{lines}**: `{line.strip()}`",
                              file=logfile)
                        failcount += 1
                    elif sussufix:
                        print(colored("FAIL:", "red"),
                              f"{susprefix} seem(s) like a multichar "
                              "prefix tag but is missing from the "
                              "Multichar_Symbols section "
                              f"on line {lines}:\n",
                              colored(line, "cyan"))
                        print(f"1. `{susprefix}` seems like multichars "
                              "prefix tag missing from declarations, on:"
                              f"**{lexcfilename}.{lines}**: `{line.strip()}`",
                              file=logfile)
                        failcount += 1
                for flag in re.findall(ATFLAGATRE, deep):
                    if flag not in declaredmultichars:
                        print(colored("FAIL:", "red"),
                              f"{flag} seems like a multichar "
                              "flag diacritic but is missing from the "
                              "Multichar_Symbols section "
                              f"on line {lines}:\n",
                              colored(line, "cyan"))
                        print(f"1. `{susprefix}` seems like multichar "
                              "flag diacritic missing from declarations, on:"
                              f"**{lexcfilename}.{lines}**: `{line.strip()}`",
                              file=logfile)
                        failcount += 1
                    if not atflagattags:
                        print("found no flag diacritics in alphabets!")
            if len(fields) <= 2:
                # continuation class and ;
                continue
    if failcount == 0:
        print("No missing multichars found.\n", file=logfile)
    return failcount


def dostuff(options: Namespace, logfile: TextIO):
    """Test multichar symbols in lexc file defined by config.json."""
    configuration = json.load(options.config)
    if "lexcroot" not in configuration:
        print(colored("SKIP", "cyan"), "lexcroot missing from config: "
              f"{options.config.name}")
        sys.exit(77)
    rootfilename = configuration["lexcroot"]
    print(f"# Multichar_Symbols tests for {basename(rootfilename)}\n",
          file=logfile)
    start = time()
    failcount = 0
    declaredmultichars: set[str] = set()
    with open(rootfilename, encoding="UTF-8") as lexcroot:
        declaredmultichars = read_multichar_symbols(lexcroot, options, logfile,
                                                    failcount)
        failcount += check_multichar_symbols(lexcroot, declaredmultichars,
                                            options, logfile)
    for key, value in configuration.items():
        if key in ["verbs", "nouns", "propernouns", "adjectives"]:
            if "lexcfile" in value:
                with open(value["lexcfile"], encoding="UTF-8") as lexcfile:
                    failcount += check_multichar_symbols(
                            lexcfile, declaredmultichars, options, logfile)
        elif key == "otherlexcs":
            for lexcfilename in value:
                with open(lexcfilename, encoding="UTF-8") as lexcfile:
                    failcount += check_multichar_symbols(
                            lexcfile, declaredmultichars, options, logfile)
    end = time()
    if options.verbose:
        print(f"Used {end - start} times")
    if not declaredmultichars:
        print(colored("SKIP:", "cyan"),
              "could not find multichars in",
              colored(rootfilename, "magenta"))
        sys.exit(77)
    print("\n## Configuration and statistics\n", file=logfile)
    print("* symbols found in declarations: `", ", ".join(declaredmultichars),
          "`", file=logfile)
    print("* `config.json` prettyprinted:", file=logfile)
    print("```json", file=logfile)
    print(prettyprint_json(configuration), file=logfile)
    print("```", file=logfile)
    if failcount > 0:
        print(colored("FAIL:", "red"),
              f"there were {failcount} problems (see above).")
        print("Fix multichars in the root lexc file:",
              colored(rootfilename, "magenta"))
        print(f"see {logfile.name} for details")
        print(f"\n**Total failures: {failcount} to be fixed in root lexc "
              f"{basename(rootfilename)} or relevant lexc file (see above)",
              file=logfile)
        if options.editor:
            print(f"Running: {options.editor} {logfile.name}")
            Popen([options.editor, logfile.name])
        sys.exit(1)
    else:
        print(colored("PASS:", "green"))
        sys.exit(0)


if __name__ == "__main__":
    main()
