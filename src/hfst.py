#!/usr/bin/env python3
"""Functions for handling HFST stuff."""

import hfst


def load_hfst(filename: str) -> hfst.HfstTransducer:
    """Load HFST automaton from a named file."""
    try:
        his = hfst.HfstInputStream(filename)
        return his.read()
    except hfst.exceptions.NotTransducerStreamException:
        raise IOError(2, filename) from None


if __name__ == "__main__":
    pass
