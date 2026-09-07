# Changelog

All notable changes to this project will be documented in this file.

## 0.11.0 - 2026-09-07

### Changed

- `gtlemmatest` / `gtspelltest`: `-B/--time-out` default raised from 60 to 300
  seconds. It is a hang guard, not a routine cutoff — a 60 s limit was
  truncating healthy large suites on loaded CI runners, publishing a partial
  `success_pct` as if it were complete. Use `-Q/--oov-limit` for a
  deterministic early bail on a broken generator.

### Fixed

- `gtlemmatest`: `success_pct` could go negative (down to `-100`) for a suite
  where every tested lemma failed. Each no-generation lemma was counted once as
  an oov and again as a miss, so `oovs + misses` exceeded the lemmas tested.
  oovs and misses are now disjoint; the rate floors at 0.

## 0.10.0 - 2026-08-31

### Added

- `gtlemmatest` and `gtspelltest` accept `-J/--json-file` to write a
  machine-readable JSON report alongside the markdown log (`-L`). The JSON
  carries per-suite statistics and structured per-lemma failures (no-generation
  / wrong-generation / analyses for lemma tests; suggestions for speller
  tests), so downstream tooling does not have to parse the markdown.

### Changed

- `gtlemmatest`: extracted the per-lemma checking into `generation_failures()`
  / `report_analyses()` / `check_lemma()` helpers. No change to the markdown
  output except that analyser readings are now listed in a stable order.

### Fixed

- `gtlemmatest`: the final FAIL/SUCCESS summaries printed the last lemma's
  mismatch *set* instead of the wrong-lemma *count* (`{mismatches}` →
  `{misses}`).

### Tests

- Added unit and integration tests for the lemma-test logic and the JSON
  output.

## 0.6.7 - 2026-04-27

### Changed

- Extended default spelltest exclusions to also remove entries tagged with `+CmpNP/Pref`, `+CmpNP/Suff`, and `+CmpNP/Only`.

## 0.6.6 - 2026-04-27

### Fixed

- Fixed parsing of speller output lines so multiword inputs are kept intact when reading `Input:` lines.
- Fixed false error reporting where only the first token of a multiword input was logged as the failing lemma.

### Changed

- Extended default spelltest exclusions to remove entries tagged with `+Use/MT`, `+Use/Marg`, `+Use/TTS`, `+Use/PMatch`, and `+Use/GC`.
- Kept `+Use/-Spell` exclusion and aligned all listed `+Use/*` tags to the same behavior in spelltest filtering.

### Tests

- Added regression tests for multiword `Input:` parsing.
- Added regression tests verifying exclusion of non-speller `+Use/*` entries from test data.
