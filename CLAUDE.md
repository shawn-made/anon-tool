# AnonTool Development Instructions

You're building **AnonTool** — a local file anonymization/de-anonymization CLI tool powered by spaCy NER with optional Ollama LLM enhancement.

## What It Does

1. **Anonymize mode**: User feeds in a file. App detects person and company names using spaCy NER + regex. Replaces them with consistent pseudonyms (e.g., "John Smith" -> "Person_A", "Acme Corp" -> "Company_1"). Outputs a clean anonymized text file.
2. **De-anonymize mode**: User feeds in a previously anonymized file. App reads the mapping key file. Replaces pseudonyms back with real names. Outputs a restored file.
3. **Mapping persistence**: A JSON key file is saved per anonymization run, linking pseudonyms to originals. This key is reused across future files so the same person/company always gets the same pseudonym.

## Architecture

- **Interface**: Python CLI (argparse) — no web UI
- **Detection**: spaCy NER (PERSON, ORG) + regex patterns (email, phone)
- **LLM (optional)**: Ollama (local, no API keys) for enhanced name verification
- **Storage**: JSON mapping files in `~/.anontool/mappings/`
- **Output**: Anonymized text files in `~/.anontool/output/`

## Project Structure

```
backend/
  app/
    __init__.py
    main.py              # CLI entry point (argparse)
    services/
      __init__.py
      detector.py        # spaCy NER + regex name detection pipeline
      anonymizer.py      # Core anonymize/de-anonymize logic
      mapping_store.py   # JSON key file read/write/lookup
      ollama_client.py   # Optional Ollama LLM client for enhanced detection
  tests/
    __init__.py
    conftest.py          # Shared fixtures (sample texts, temp dirs)
    test_detector.py
    test_anonymizer.py
    test_mapping_store.py
    test_ollama_client.py
    test_integration.py
requirements.txt
.env.example
CLAUDE.md
TASKS.md
DECISIONS.md
QUESTIONS_LOG.md
```

## Key Patterns

1. **Layered detection pipeline**: regex (emails, phones) -> spaCy NER (PERSON, ORG) -> deduplication of overlapping spans. This is proven architecture from a prior project.

2. **Consistent pseudonym mapping**: When anonymizing, always check existing mapping first. Same input name = same pseudonym across all files using that mapping ID. New names get the next sequential pseudonym (Person_A, Person_B, etc.).

3. **Reversible by design**: Every anonymize() call produces or updates a JSON key file. The deanonymize() function reads that same key file. Round-trip fidelity is a hard requirement.

4. **Ollama is optional**: The tool MUST work without Ollama running. spaCy is the primary detection engine. Ollama is an enhancement layer that can verify borderline NER detections. Check for Ollama availability at runtime and gracefully fall back.

5. **Right-to-left replacement**: When replacing names in text, process entities from end to start to preserve character offsets. This is critical for correct replacement.

## Rules

- All mapping files stay local — never transmitted anywhere
- Ollama must be optional — tool works without it (spaCy-only fallback)
- No hardcoded paths — use `~/.anontool/` convention with Path.home()
- All config from `.env` (Ollama URL, model name, paths)
- Test every feature with pytest
- Run `ruff check .` after every task — no lint warnings
- Write docstrings for all public functions

## Development Workflow

- Check `TASKS.md` for current task and progress
- Work through tasks sequentially (Task 1 -> Task 8)
- For each task: implement -> write tests -> run tests -> lint -> mark complete
- Run tests: `cd backend && python -m pytest tests/ -v`
- Lint: `cd backend && ruff check .`
- Fix lint: `cd backend && ruff check . --fix`
- Document any non-obvious decisions in `DECISIONS.md`

## Detection Reference

The detection pipeline follows this proven pattern (from a prior anonymization project):

```
detect_regex(text)     -> list of (email, phone, URL) entities
detect_ner(text)       -> list of (PERSON, ORG) entities via spaCy
deduplicate(entities)  -> merge overlapping spans, prefer longer matches
```

spaCy confidence heuristics:
- Multi-word entities (e.g., "John Smith") -> high confidence (~0.90)
- Single capitalized word (e.g., "Smith") -> medium confidence (~0.80)
- Single lowercase/short word -> low confidence (~0.60), skip or flag
