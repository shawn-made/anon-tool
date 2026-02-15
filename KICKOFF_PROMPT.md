# AnonTool — Kickoff Prompt

Copy and paste this into Claude Code to start the build:

---

I want you to build AnonTool end-to-end following CLAUDE.md and TASKS.md. Work through each task sequentially (Task 1 through Task 8). For each task:

1. Read the task requirements from TASKS.md
2. Implement the code
3. Write tests
4. Run tests and lint (`python -m pytest tests/ -v` and `ruff check .`)
5. Fix any failures until green
6. Mark the task complete in TASKS.md (update the checkboxes AND the progress table)
7. Move to the next task

Key context:
- This is a LOCAL file anonymization tool — no cloud, no API keys needed for core functionality
- spaCy en_core_web_sm is the primary detection engine — install it during Task 1 setup
- Ollama (Task 6) is an optional enhancement — the tool MUST work without it
- All mapping data stays in ~/.anontool/mappings/ as JSON files
- CLI interface (argparse), not a web UI
- Reference the detection pipeline architecture described in CLAUDE.md

Start with Task 1 now. Do not ask me questions — make reasonable decisions and document any assumptions in DECISIONS.md. If something is truly ambiguous, bias toward the simpler option.
