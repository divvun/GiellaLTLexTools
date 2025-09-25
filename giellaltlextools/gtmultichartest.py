#!/usr/bin/env python3
"""GiellaLT tests for multichars in lexc."""

import re
import sys
from argparse import ArgumentParser
from time import time


def main():
    """CLI for GiellaLT lemma generation tests."""
    argp = ArgumentParser()
    argp.add_argument("-l", "--lexc", type=open, dest="lexcfile",
                      help="read multichars from lexc file",
                      required=True)
    argp.add_argument("-d", "--debug", action="store_true", default=False,
                      help="prints debugging outputs")
    argp.add_argument("-v", "--verbose", action="store_true", default=False,
                      help="prints some outputs")
    options = argp.parse_args()
    start = time()
    inmultichars = False
    inlexicons = False
    failcount = 0
    declaredmultichars = set()
    lines = 0
    for line in options.lexcfile:
        lines += 1
        if not inmultichars and not inlexicons:
            if line.startswith("Multichar_Symbols"):
                inmultichars = True
                rest = line[len("Multichar_Symbols") + 1:].strip()
                if "!" in rest:
                    rest = rest.split("!")[0].strip()
                if rest != "":
                    print(f"trailing rubbish after multichar syms: {rest}")
                    failcount += 1
            elif line.startswith("LEXICON"):
                print(f"found lexicons before multichars: {line.strip()}")
                failcount += 1
                inlexicons = True
            else:
                continue
        elif inmultichars and not inlexicons:
            if line.startswith("LEXICON "):
                inmultichars = False
                inlexicons = True
                continue
            if "!" in line:
                line = line.replace("%!", "§EXCLAMATION§")
                line = line.split("!")[0]
                line = line.replace("§EXCLAMATION§", "%!")
            line = line.replace("% ", "§SPACE§")
            for multichar in line.split():
                multichar = multichar.replace("§SPACE§", "% ")
                declaredmultichars.add(multichar)
        elif not inmultichars and inlexicons:
            if ";" in line:
                if "!" in line:
                    line = line.replace("%!", "§EXCLAMATION§")
                    line = line.split("!")[0]
                    line = line.replace("§EXCLAMATION§", "%!")
                line = line.replace("%;", "§SEMICOLON§")
                if line.count(";") > 1:
                    print(f"too many semicolons on line {lines}:\n{line}")
                    failcount += 1
                    continue
                line = line.replace("§SEMICOLON§", "%;")
                if "\"" in line:
                    line = line.replace("%\"", "§QUOTATION§")
                    line = re.sub(" \"[^\"]*\"", "", line)
                    line = line.replace("§QUOTATION§", "\"")
                if "<" in line:
                    line = line.replace("%<", "§LESSTHAN§")
                    line = line.replace("%>", "§MORETHAN§")
                    line = re.sub("<[^>]*>", "§REGEX§", line)
                    line = line.replace("§LESSTHAN§", "%<")
                    line = line.replace("§MORETHAN§", "%>")
                elif ">" in line:
                    line = line.replace("%>", "§MORETHAN§")
                    if ">" in line:
                        line = re.sub("^[^>]*>", "§REGEXFAIL", line)
                    line = line.replace("§MORETHAN§", "%>")
                if "% " in line:
                    line = line.replace("% ", "§SPACE§")
                pairstring = None
                fields = line.split()
                for i, field in enumerate(fields):
                    if field == ";":
                        if i >= 1:
                            cont = fields[i-1]
                        if i >= 2:
                            pairstring = fields[i-2]
                        if i >= 3:
                            if line.startswith("LEXICON "):
                                print("entries on LEXICON line is not "
                                      f"supported:\n{line}")
                            else:
                                print(f"too many spaces? parsing:\n{line}")
                                failcount += 1
                if pairstring:
                    if ":" in pairstring:
                        deep = pairstring.split(":")[0]
                    else:
                        deep = pairstring
                    tagre = r"\+[A-Za-z0-9_-][^+@#]*"
                    for tag in re.findall(tagre, deep):
                        if tag not in declaredmultichars:
                            if not tag[-1].isalpha() and \
                                    tag[:-1] in declaredmultichars:
                                continue
                            print(f"{tag} seems like a multichar but is missing"
                                  " from the Multichar_Symbols section "
                                  f"on line {lines}:\n{line}")
                            failcount += 1
                if len(fields) <= 2:
                    # continuation class and ;
                    continue
    end = time()
    print(f"Used {end - start} times")
    if lines == 0:
        print(f"SKIP: could not find multichars in {options.lexcfile.name}")
        sys.exit(77)
    if failcount > 0:
        print("FAIL: there were problems (see above).")
        sys.exit(1)


if __name__ == "__main__":
    main()
