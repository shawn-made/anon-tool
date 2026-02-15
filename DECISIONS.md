# AnonTool — Decisions Log

Track architectural and implementation decisions made during development.

---

## D1: Two-pass replacement strategy (Task 4/8)

**Context**: spaCy's `en_core_web_sm` model doesn't detect names in all contexts — especially bulleted lists, headings, and parenthetical formats (e.g., `- Bob Thompson (Engineering Lead, ...)`). Position-based right-to-left replacement only covers detected positions.

**Decision**: Added a second replacement pass after position-based replacement. After the right-to-left pass, we do a simple `str.replace()` for all mapped names (longest first). This catches any occurrences spaCy missed.

**Trade-off**: Slight risk of replacing text that coincidentally matches a mapped name but isn't actually PII. Accepted because: (a) the mapping only contains names that were legitimately detected at least once, and (b) round-trip fidelity is a hard requirement.

---

## D2: Pseudonym naming scheme — letters for people, numbers for others (Task 3)

**Context**: Needed a systematic pseudonym format that's consistent and human-readable.

**Decision**: PERSON entities use letter suffixes (Person_A, Person_B, ..., Person_Z, Person_AA). ORG/EMAIL/PHONE use numeric suffixes (Company_1, Email_1, Phone_1). This makes it easy to visually distinguish entity types in anonymized text.

---

## D3: File I/O functions in anonymizer.py, not a separate module (Task 5)

**Context**: CLAUDE.md structure suggests file operations are separate, but the file I/O functions are thin wrappers around `anonymize_text`/`deanonymize_text`.

**Decision**: Added `anonymize_file()` and `deanonymize_file()` directly to `anonymizer.py` to avoid an extra module with tight coupling. They handle path resolution, file reading/writing, and delegation to the text functions.

---

## D4: spaCy model loaded once at module level (Task 2)

**Context**: `spacy.load()` is expensive (~200ms). Loading per-call would be slow.

**Decision**: Load the model once as `_nlp` at the module level in `detector.py`. The small model (`en_core_web_sm`) uses ~50MB RAM which is acceptable for a CLI tool.

---

## D5: Ollama integration as lazy import (Task 6)

**Context**: Ollama is optional. Importing `OllamaClient` at the top of `anonymizer.py` would fail if httpx isn't installed or cause unnecessary overhead.

**Decision**: Ollama import happens inside the `if use_ollama:` block in `anonymize_text()`. This ensures the tool works without Ollama and doesn't pay the import cost when it's not needed.

---

## D6: CLI uses subprocess for integration tests (Task 7)

**Context**: Could test CLI via direct function calls to `main()`, or via subprocess.

**Decision**: Used subprocess to test the actual CLI entry point (`python -m app.main`). This tests the real argparse parsing, module loading, and exit codes. Slower but higher confidence.

---

## D7: Bulk folder processing — per-file processing with disk-based mapping accumulation (Post-MVP)

**Context**: User has ~165 hour-long transcript files to anonymize. Merging them first would exceed spaCy's 1M character limit. Needed a way to process individually but output to one merged file with consistent pseudonyms.

**Decision**: `anonymize_folder()` loops through files, calling `anonymize_text()` for each with the same `mapping_id`. The existing `MappingStore` pattern (load from disk → add entries → save to disk) naturally accumulates mappings across calls. No changes to `anonymize_text()` or `MappingStore` signatures were needed.

**Trade-off**: 165 disk read/write cycles for the mapping file. Trivial I/O cost for this scale. If performance becomes an issue with thousands of files, could refactor to pass a `MappingStore` instance directly.

---

## D8: File creation time sorting — st_birthtime with ctime fallback (Post-MVP)

**Context**: User wants files sorted by creation date in the merged output. macOS provides `st_birthtime` (true creation time), but Linux uses `st_ctime` (metadata change time, not creation).

**Decision**: Helper `_get_file_creation_time()` tries `st_birthtime` first (macOS), falls back to `st_ctime` (Linux/Windows). Since the user is on macOS, this gives accurate creation-time sorting.

---

## Final Summary

**Architecture**: Layered detection (regex → spaCy NER → dedup → optional Ollama verification) with two-pass replacement proved robust. Round-trip fidelity holds for all 3 sample documents.

**Test coverage**: 129 tests across 7 test files:
- 29 detector tests (regex, NER, confidence, dedup, pipeline)
- 21 mapping store tests (create, load, pseudonyms, persistence, reverse lookup)
- 17 anonymizer tests (anonymize, deanonymize, round-trip)
- 10 file I/O tests
- 12 Ollama client tests (all mocked)
- 10 CLI integration tests (subprocess)
- 8 end-to-end integration tests
- 22 bulk anonymize tests (folder processing, sorting, CLI)

**Known limitations**:
- spaCy `en_core_web_sm` has false positives (e.g., "Agenda" as PERSON, "Q4" as ORG). The second-pass replacement mitigates this for round-trip correctness, but the mapping may contain spurious entries.
- Single-word names in ambiguous contexts may be missed or over-detected.
- Ollama verification could improve accuracy but requires a running Ollama instance.
