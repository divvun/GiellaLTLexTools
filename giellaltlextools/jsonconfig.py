#!/usr/bin/env python3
"""Functions for handling json configs."""


import json
from os.path import basename, dirname


def prettyprint_json(config) -> str:
    """prettyprint json so it doesn't have local paths and is stable-ish."""
    for pos in ["verbs", "nouns", "adjectives", "propernouns"]:
        if pos in config:
            config[pos]["lexcfile"] = ".../" + \
                prettyprint_lexcfilename(config[pos]["lexcfile"])
    if "generator" in config:
        config["generator"] = ".../" + basename(config["generator"])
    if "analyser" in config:
        config["analyser"] = ".../" + basename(config["analyser"])
    if "lexcroot" in config:
        config["lexcroot"] = ".../" + \
            prettyprint_lexcfilename(config["lexcroot"])
    if "otherlexcs" in config:
        for i, lexc in enumerate(config["otherlexcs"]):
            config["otherlexcs"][i] = ".../" + prettyprint_lexcfilename(lexc)
    if "lexcfiles" in config:
        for i, lexc in enumerate(config["lexcfiles"]):
            config["lexcfiles"][i] = ".../" + prettyprint_lexcfilename(lexc)
    if "zhfstfiles" in config:
        config["zhfstfile"] = ".../" + basename(config["zhfstfile"])
    return json.dumps(config, indent=4, sort_keys=True)


def prettyprint_lexcfilename(s: str) -> str:
    """Pretty print absolute lexc path to hide home dirs and stuff."""
    rv = basename(s)
    if rv not in ["root.lexc", "compounding.lexc"]:
        rv = basename(dirname(s)) + "/" + rv
    return rv
