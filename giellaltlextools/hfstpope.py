#!/usr/bin/env python3
"""Functions for handling HFST stuff as subprocess just."""

from subprocess import Popen, PIPE

class Transducer:
    def __init__(self):
        self.pipes = None

    def load(self, filename: str):
        self.pipes = Popen(["hfst-lookup", "-q", filename], stdout=PIPE,
                           stdin=PIPE)

    def lookup(self, s: str):
        if not self.pipes:
            raise RuntimeError  # or something idk
        s = s + "\n"
        self.pipes.stdin.write(s.encode("UTF-8"))
        self.pipes.stdin.flush()
        reading = True
        analyses = []
        while reading:
            line = self.pipes.stdout.readline().decode("UTF-8")
            if line=="":
                reading = False
                break
            fields = line.split("\t")
            if len(fields) == 3:
                if fields[1].endswith("+?") or fields[2] == "inf":
                    continue
                else:
                    fields[2] = fields[2].replace(",", ".")
                    analyses.append([fields[1], float(fields[2])])
            elif len(fields) == 2:
                if fields[1].endswith("+?"):
                    continue
                else:
                    analyses.append([fields[1], 0.0])
            elif line.strip() == "":
                reading = False
            else:
                print(f"weird output from hfst-lookup -q: {line}")
        return analyses

def load_hfst_pope(filename: str) -> Transducer:
    """Load HFST automaton from a named file."""
    t = Transducer()
    t.load(filename)
    return t

if __name__ == "__main__":
    pass
