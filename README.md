# GiellaLTLexTools

Scripts for testing lexicony stuff in giellalt plus some processing lexc python
scripts.

## Dependencies

Uses [pyhfst]() to load HFST automata. You can install pyhfst with [pip]().
Spell-checker testing uses
[divvunspell](https://github.com/divvun/divvunspell) binaries. You can install
divvunspell with [cargo]().

## Installation

You can install giellaltlextools with [pipx](): `pipx install
git+https://github.com/divvun/giellaltlextools`.

## Usage

Mainly from `make check` in GiellaLT infra.

There are currently three programs installed:

- `gtlemmatest` for testing that a generator generates lemmas found from a lexc
  file
- `gtparadigmteset` for testing that a generator generates full paradigms of the
  lemmas
- `gtspelltest` for testing that a spell checker accepts lemmas from lexc files.


### Lemma testing

```console
$ gtlemmatest -l src/fst/morphology/stems/nouns.lexc \
    -a src/fst/analyser-gt-desc.hfstol \
    -g src/fst/generator-gt-desc.hfstol \
    -t +N+Sg+Nom -t +N+Pl+Nom
```

The lexc files should mainly contain lexc lines that contain full lemma forms.

### Paradigm testing

```console
$ gtparadigmtest -l src/fst/morphology/stens/nouns.lexc \
    -p src/fst/morphology/test/testnounparadigm.txt \
    -g src/fst/generator-gt-desc.hfstol
```

The lexc files should mainly contain lexc lines that contain full lemma forms.

### Spell-checker lemma testing

```console
$ gtspelltest -z tools/spellcheckers/se.zhfst -D divvunspell \
    src/fst/morphology/stems/*.lexc
```

The lexc files should mainly contain lexc lines that contain full lemma forms.
