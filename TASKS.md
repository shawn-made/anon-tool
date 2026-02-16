# AnonTool — Tasks

**Method**: Sequential task execution with tests at every step

## Progress

| Group | Tasks | Done | Status |
|-------|-------|------|--------|
| Setup | 1 | 1/1 | Complete |
| Core Detection | 2 | 1/1 | Complete |
| Mapping | 3 | 1/1 | Complete |
| Anonymization | 4-5 | 2/2 | Complete |
| Enhancement | 6 | 1/1 | Complete |
| Interface | 7 | 1/1 | Complete |
| Polish | 8 | 1/1 | Complete |
| Bulk Processing | 9 | 1/1 | Complete |
| Web UI | 10 | 1/1 | Complete |
| Large File Support | 11 | 1/1 | Complete |
| Email Detection Fix | 12 | 1/1 | Complete |

---

## Task 1: Project Scaffolding
- [x] Python project structure (`backend/app/services/`, `backend/tests/`)
- [x] `__init__.py` files in all packages
- [x] `requirements.txt` with pinned dependencies
- [x] `.env.example` with `OLLAMA_URL` and `OLLAMA_MODEL`
- [x] `~/.anontool/` directory creation on first run (mappings/, output/)
- [x] `conftest.py` with sample text fixtures and temp directory fixture
- [x] Verify: `python -m pytest tests/` runs successfully (0 tests collected is OK)
**Done when**: Project structure exists, pytest runs without errors, ruff clean

---

## Task 2: Name Detection — spaCy + Regex
- [x] `detector.py` with `detect_entities(text) -> list[DetectedEntity]`
- [x] `DetectedEntity` dataclass: text, entity_type, start, end, confidence, source
- [x] Regex detection for EMAIL and PHONE patterns
- [x] spaCy NER detection for PERSON and ORG entities
- [x] Confidence estimation (multi-word = 0.90, single capitalized = 0.80, other = 0.60)
- [x] Deduplication: overlapping spans merged, prefer longer match + higher confidence
- [x] Filter out low-confidence single-word detections (< 0.65)
- [x] 15+ unit tests covering: simple names, multi-word names, emails, phones, mixed text, edge cases (no PII, all PII, overlapping entities)
**Done when**: `python -m pytest tests/test_detector.py -v` — all pass, detects names in 3+ sample paragraphs

---

## Task 3: Mapping Store — JSON Key Files
- [x] `mapping_store.py` with `MappingStore` class
- [x] `create_or_load(mapping_id: str) -> dict` — loads existing JSON or creates empty
- [x] `get_pseudonym(real_name: str, entity_type: str) -> str` — returns existing or creates new
- [x] Pseudonym format: `Person_A`, `Person_B`, ... `Person_Z`, `Person_AA` for people; `Company_1`, `Company_2` for orgs; `Email_1`, `Phone_1` for regex types
- [x] `save(mapping_id: str)` — writes mapping to `~/.anontool/mappings/{mapping_id}.json`
- [x] `list_mappings()` — returns all available mapping IDs
- [x] JSON format: `{"mapping_id": "...", "created": "...", "updated": "...", "entries": {"real_name": {"pseudonym": "...", "type": "..."}}}`
- [x] 10+ unit tests with temp directories
**Done when**: Same name across two calls returns same pseudonym; JSON file persists correctly

---

## Task 4: Anonymizer — Core Logic
- [x] `anonymizer.py` with `anonymize_text(text: str, mapping_id: str) -> AnonymizeResult`
- [x] `AnonymizeResult` dataclass: anonymized_text, entities_found, mapping_id
- [x] `deanonymize_text(text: str, mapping_id: str) -> str`
- [x] Anonymize flow: detect entities -> get pseudonyms from mapping -> replace right-to-left
- [x] Deanonymize flow: load mapping -> build reverse lookup -> replace all pseudonyms
- [x] Handle edge case: pseudonym substring of another (replace longest first)
- [x] Round-trip test: `deanonymize(anonymize(text)) == text`
- [x] 12+ unit tests including edge cases (empty text, no entities, repeated names, mixed types)
**Done when**: Round-trip works on 3 sample documents with mixed PII types

---

## Task 5: File I/O — Read and Write Files
- [x] `anonymize_file(input_path, output_path=None, mapping_id=None) -> output_path`
- [x] `deanonymize_file(input_path, output_path=None, mapping_id=str) -> output_path`
- [x] Auto-generate output path if not specified: `~/.anontool/output/{original_name}.anon.txt`
- [x] Auto-generate mapping_id if not specified: based on input filename + timestamp
- [x] Support `.txt` and `.md` file extensions
- [x] Preserve original file (never modify input)
- [x] Print summary after operation: entities found, output path, mapping ID
- [x] 8+ tests with temp files
**Done when**: Can anonymize a .txt file, verify output has no real names, deanonymize it back to original

---

## Task 6: Ollama Integration (Optional Enhancement)
- [x] `ollama_client.py` with `OllamaClient` class
- [x] `is_available() -> bool` — health check against Ollama API
- [x] `verify_entities(text: str, entities: list) -> list` — ask LLM to confirm/reject borderline detections
- [x] Prompt: "Given this text, are these detected names actually person/company names? Respond with JSON."
- [x] Integrate into detection pipeline: after spaCy, optionally run Ollama verification
- [x] Graceful fallback: if Ollama not running, skip verification silently (log a note)
- [x] Config from .env: `OLLAMA_URL`, `OLLAMA_MODEL` (default: llama3.1:8b)
- [x] 6+ tests with mocked Ollama responses
**Done when**: Works identically with and without Ollama running; verification improves accuracy when available

---

## Task 7: CLI Interface
- [x] `main.py` using argparse with subcommands
- [x] `python -m app.main anonymize <input_file> [--mapping-id ID] [--output PATH] [--use-ollama]`
- [x] `python -m app.main deanonymize <input_file> --mapping-id ID [--output PATH]`
- [x] `python -m app.main list-mappings`
- [x] `python -m app.main show-mapping <mapping_id>` — display a mapping's contents
- [x] Colored terminal output (entity counts, file paths) — use simple ANSI codes, no extra deps
- [x] Helpful error messages (file not found, mapping not found, Ollama not running)
- [x] `--help` text is clear and complete
- [x] 5+ CLI integration tests using subprocess
**Done when**: Full CLI flow works end-to-end for anonymize and deanonymize

---

## Task 8: Integration Test & Polish
- [x] Create 3 realistic sample documents in `backend/tests/samples/` (business email, meeting notes, project report)
- [x] End-to-end test: anonymize each sample -> verify no real names in output -> deanonymize -> verify matches original
- [x] Verify mapping persistence: anonymize file A, then file B with same mapping -> shared names have same pseudonyms
- [x] Lint clean: `ruff check .` with zero warnings
- [x] All tests pass: `python -m pytest tests/ -v`
- [x] Test count sanity check: expect 60+ total tests (actual: 107)
- [x] Write final summary in DECISIONS.md
**Done when**: All tests green, lint clean, 3 sample docs round-trip perfectly, 60+ tests total

---

## Task 9: Bulk Folder Anonymization
- [x] `anonymize_folder()` in `anonymizer.py` — process all files in a folder with shared mapping
- [x] Sort files by creation date (`st_birthtime` on macOS, `st_ctime` fallback)
- [x] Merge all outputs into single file with `=== filename ===` section headers
- [x] `bulk-anonymize` CLI subcommand with progress output
- [x] `BulkAnonymizeResult` dataclass with per-file and aggregate stats
- [x] 22 tests in `test_bulk_anonymize.py`
**Done when**: Point at a folder, get one merged anonymized file sorted by creation date

---

## Task 10: Web UI (Flask)
- [x] `web.py` Flask server with routes: `GET /`, `POST /anonymize`, `POST /deanonymize`, `GET /mappings`
- [x] `templates/index.html` — single-page UI with mode toggle, file upload, output folder selector
- [x] Multi-file upload with merge option
- [x] Mapping ID dropdown for de-anonymize mode
- [x] JSON error responses (global error handler instead of HTML 500s)
- [x] Desktop launcher (`AnonTool.command`) for one-click startup
- [x] 12 tests in `test_web.py`
- [x] Runs on port 8080 (avoids macOS AirPlay conflict on 5000)
**Done when**: Upload a file in the browser, get anonymized output, de-anonymize with mapping dropdown

---

## Task 11: Large File Chunking
- [x] `_split_into_chunks()` in `detector.py` — split text at line boundaries into ~900K char chunks
- [x] Adjusted `_detect_ner()` to process chunks with character offset correction
- [x] Handles files exceeding spaCy's 1M character limit (tested with 12M char file)
**Done when**: 12M character transcript processes without spaCy E088 error

---

## Task 12: Email-Inside-ORG Detection Fix
- [x] `_is_inside_email()` guard in `detector.py`
- [x] Prevents ORG/PERSON entities embedded in email addresses from being replaced independently
- [x] 9 new tests (5 in `TestIsInsideEmail`, 4 in `TestDeduplication`)
**Done when**: Domain names inside emails are not separately anonymized as ORGs

---

## Current Stats
- **Total tests**: 150
- **Lint**: Clean
- **Interfaces**: CLI + Web UI (port 8080)
