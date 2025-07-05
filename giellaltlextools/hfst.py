#!/usr/bin/env python3
"""Functions for handling HFST stuff."""

import pyhfst


def load_hfst(filename: str) -> pyhfst.Transducer:
    """Load HFST automaton from a named file."""
    his = pyhfst.HfstInputStream(filename)
    return his.read()


if __name__ == "__main__":
    pass
