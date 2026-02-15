# AnonTool — MVP Tasks

**Target**: Single-session build (all 8 tasks)
**Method**: Sequential task execution with tests at every step

## Progress

| Group | Tasks | Done | Status |
|-------|-------|------|--------|
| Setup | 1 | 0/1 | Not started |
| Core Detection | 2 | 0/1 | Not started |
| Mapping | 3 | 0/1 | Not started |
| Anonymization | 4-5 | 0/2 | Not started |
| Enhancement | 6 | 0/1 | Not started |
| Interface | 7 | 0/1 | Not started |
| Polish | 8 | 0/1 | Not started |

---

## Task 1: Project Scaffolding
- [ ] Python project structure (`backend/app/services/`, `backend/tests/`)
- [ ] `__init__.py` files in all packages
- [ ] `requirements.txt` with pinned dependencies
- [ ] `.env.example` with `OLLAMA_URL` and `OLLAMA_MODEL`
- [ ] `~/.anontool/` directory creation on first run (mappings/, output/)
- [ ] `conftest.py` with sample text fixtures and temp directory fixture
- [ ] Verify: `python -m pytest tests/` runs successfully (0 tests collected is OK)
**Done when**: Project structure exists, pytest runs without errors, ruff clean

---

## Task 2: Name Detection — spaCy + Regex
- [ ] `detector.py` with `detect_entities(text) -> list[DetectedEntity]`
- [ ] `DetectedEntity` dataclass: text, entity_type, start, end, confidence, source
- [ ] Regex detection for EMAIL and PHONE patterns
- [ ] spaCy NER detection for PERSON and ORG entities
- [ ] Confidence estimation (multi-word = 0.90, single capitalized = 0.80, other = 0.60)
- [ ] Deduplication: overlapping spans merged, prefer longer match + higher confidence
- [ ] Filter out low-confidence single-word detections (< 0.65)
- [ ] 15+ unit tests covering: simple names, multi-word names, emails, phones, mixed text, edge cases (no PII, all PII, overlapping entities)
**Done when**: `python -m pytest tests/test_detector.py -v` — all pass, detects names in 3+ sample paragraphs

---

## Task 3: Mapping Store — JSON Key Files
- [ ] `mapping_store.py` with `MappingStore` class
- [ ] `create_or_load(mapping_id: str) -> dict` — loads existing JSON or creates empty
- [ ] `get_pseudonym(real_name: str, entity_type: str) -> str` — returns existing or creates new
- [ ] Pseudonym format: `Person_A`, `Person_B`, ... `Person_Z`, `Person_AA` for people; `Company_1`, `Company_2` for orgs; `Email_1`, `Phone_1` for regex types
- [ ] `save(mapping_id: str)` — writes mapping to `~/.anontool/mappings/{mapping_id}.json`
- [ ] `list_mappings()` — returns all available mapping IDs
- [ ] JSON format: `{"mapping_id": "...", "created": "...", "updated": "...", "entries": {"real_name": {"pseudonym": "...", "type": "..."}}}`
- [ ] 10+ unit tests with temp directories
**Done when**: Same name across two calls returns same pseudonym; JSON file persists correctly

---

## Task 4: Anonymizer — Core Logic
- [ ] `anonymizer.py` with `anonymize_text(text: str, mapping_id: str) -> AnonymizeResult`
- [ ] `AnonymizeResult` dataclass: anonymized_text, entities_found, mapping_id
- [ ] `deanonymize_text(text: str, mapping_id: str) -> str`
- [ ] Anonymize flow: detect entities -> get pseudonyms from mapping -> replace right-to-left
- [ ] Deanonymize flow: load mapping -> build reverse lookup -> replace all pseudonyms
- [ ] Handle edge case: pseudonym substring of another (replace longest first)
- [ ] Round-trip test: `deanonymize(anonymize(text)) == text`
- [ ] 12+ unit tests including edge cases (empty text, no entities, repeated names, mixed types)
**Done when**: Round-trip works on 3 sample documents with mixed PII types

---

## Task 5: File I/O — Read and Write Files
- [ ] `anonymize_file(input_path, output_path=None, mapping_id=None) -> output_path`
- [ ] `deanonymize_file(input_path, output_path=None, mapping_id=str) -> output_path`
- [ ] Auto-generate output path if not specified: `~/.anontool/output/{original_name}.anon.txt`
- [ ] Auto-generate mapping_id if not specified: based on input filename + timestamp
- [ ] Support `.txt` and `.md` file extensions
- [ ] Preserve original file (never modify input)
- [ ] Print summary after operation: entities found, output path, mapping ID
- [ ] 8+ tests with temp files
**Done when**: Can anonymize a .txt file, verify output has no real names, deanonymize it back to original

---

## Task 6: Ollama Integration (Optional Enhancement)
- [ ] `ollama_client.py` with `OllamaClient` class
- [ ] `is_available() -> bool` — health check against Ollama API
- [ ] `verify_entities(text: str, entities: list) -> list` — ask LLM to confirm/reject borderline detections
- [ ] Prompt: "Given this text, are these detected names actually person/company names? Respond with JSON."
- [ ] Integrate into detection pipeline: after spaCy, optionally run Ollama verification
- [ ] Graceful fallback: if Ollama not running, skip verification silently (log a note)
- [ ] Config from .env: `OLLAMA_URL`, `OLLAMA_MODEL` (default: llama3.1:8b)
- [ ] 6+ tests with mocked Ollama responses
**Done when**: Works identically with and without Ollama running; verification improves accuracy when available

---

## Task 7: CLI Interface
- [ ] `main.py` using argparse with subcommands
- [ ] `python -m app.main anonymize <input_file> [--mapping-id ID] [--output PATH] [--use-ollama]`
- [ ] `python -m app.main deanonymize <input_file> --mapping-id ID [--output PATH]`
- [ ] `python -m app.main list-mappings`
- [ ] `python -m app.main show-mapping <mapping_id>` — display a mapping's contents
- [ ] Colored terminal output (entity counts, file paths) — use simple ANSI codes, no extra deps
- [ ] Helpful error messages (file not found, mapping not found, Ollama not running)
- [ ] `--help` text is clear and complete
- [ ] 5+ CLI integration tests using subprocess
**Done when**: Full CLI flow works end-to-end for anonymize and deanonymize

---

## Task 8: Integration Test & Polish
- [ ] Create 3 realistic sample documents in `backend/tests/samples/` (business email, meeting notes, project report)
- [ ] End-to-end test: anonymize each sample -> verify no real names in output -> deanonymize -> verify matches original
- [ ] Verify mapping persistence: anonymize file A, then file B with same mapping -> shared names have same pseudonyms
- [ ] Lint clean: `ruff check .` with zero warnings
- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] Test count sanity check: expect 60+ total tests
- [ ] Write final summary in DECISIONS.md
**Done when**: All tests green, lint clean, 3 sample docs round-trip perfectly, 60+ tests total
