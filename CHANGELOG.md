# Changelog

All notable changes to this project will be documented in this file.

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
