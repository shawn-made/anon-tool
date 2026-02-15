# AnonTool — PM Learning Log

Technical concepts encountered during development, explained for a PM audience.

---

## Architecture

| Term | What It Means | When to Use It |
|------|--------------|----------------|
| NER (Named Entity Recognition) | A technique where software reads text and identifies specific types of things — like person names, company names, dates. It's like a smart highlighter that knows what category each highlighted word belongs to. | "Our anonymization tool uses NER to automatically find names in documents, so users don't have to manually tag them." |
| spaCy | An open-source Python library for natural language processing (NLP). Think of it as a pre-built engine that can read and understand text — we use its NER capability to find names. | "We chose spaCy as our NER engine because it's fast, well-maintained, and works offline — no API calls needed." |
| Detection Pipeline | A series of steps that text goes through to find all sensitive information. Like an assembly line — first regex catches emails/phones, then spaCy catches names, then we remove duplicates. Each step catches things the others miss. | "The detection pipeline layers multiple methods so we catch more PII than any single approach would." |
| Two-pass Replacement | A strategy where we replace detected items in two stages: first at exact detected positions (precise), then a sweep to catch any remaining matches the detector missed. Like proofreading a document twice — once for specific marked errors, once for anything you missed on the first pass. | "We use two-pass replacement because NER models miss some name occurrences depending on context — the second pass catches those." |
| Round-trip Fidelity | The guarantee that if you anonymize a document and then de-anonymize it, you get back exactly the original text. Like encrypting and decrypting — nothing should be lost in the process. | "Round-trip fidelity is our key quality metric — every document must survive anonymize → de-anonymize without any changes." |

---

## Data & Storage

| Term | What It Means | When to Use It |
|------|--------------|----------------|
| Mapping File | A JSON file that records which real name was replaced with which pseudonym (e.g., "John Smith" → "Person_A"). Like a decoder ring — you need it to reverse the anonymization. | "Each anonymization run produces a mapping file. Without it, you can't de-anonymize the document." |
| JSON (JavaScript Object Notation) | A standard format for storing structured data in plain text. It's human-readable — you can open it in any text editor and understand it. We use it for mapping files. | "We store mappings as JSON files so they're easy to inspect, debug, and back up." |
| Pseudonym | A fake replacement name used in place of a real name. Our tool generates them systematically (Person_A, Person_B) so the same real name always gets the same pseudonym. | "Consistent pseudonyms mean that if 'John Smith' appears in 10 documents, he's always 'Person_A' across all of them." |

---

## Security

| Term | What It Means | When to Use It |
|------|--------------|----------------|
| PII (Personally Identifiable Information) | Any data that could identify a specific person — names, emails, phone numbers, addresses. This is what our tool is designed to find and replace. | "AnonTool detects and removes PII so documents can be shared safely without exposing real identities." |
| Local-only processing | All data stays on the user's machine. Nothing is sent to cloud servers or external APIs. This is a deliberate security choice. | "Because we process everything locally, there's zero risk of PII leaking through network requests." |

---

## CLI & I/O

| Term | What It Means | When to Use It |
|------|--------------|----------------|
| CLI (Command Line Interface) | A way to interact with a program by typing text commands in a terminal, rather than clicking buttons in a graphical window. Preferred by developers for automation and scripting. | "AnonTool is a CLI tool — users run commands like `anontool anonymize report.txt` rather than using a web interface." |
| argparse | A Python library that handles command-line arguments. It parses what the user types (flags, file paths, options) and turns it into structured data the program can use. | "We use argparse to handle CLI input, so users get helpful error messages if they mistype a command." |

---

## Testing

| Term | What It Means | When to Use It |
|------|--------------|----------------|
| pytest | The most popular Python testing framework. You write small functions that check whether your code behaves correctly, then pytest runs them all and reports pass/fail. | "We use pytest to run our test suite — every feature has tests written alongside it." |
| Unit Test | A test that checks one small piece of code in isolation (one function, one method). Fast to run, easy to debug when they fail. | "Each service module has its own unit tests — if name detection breaks, we know exactly which test will fail." |
| Integration Test | A test that checks whether multiple pieces work together correctly (e.g., detection + mapping + file I/O in sequence). Slower but catches problems that unit tests miss. | "Our integration tests verify the full anonymize-then-deanonymize round-trip works end-to-end." |
| Test Fixture | Pre-built test data that's reused across multiple tests. Like a shared prop in a theater — set it up once, use it in many scenes. | "We have fixtures with sample business emails and meeting notes so every test uses realistic data." |

---

## Development Process

| Term | What It Means | When to Use It |
|------|--------------|----------------|
| Linting (ruff) | Automated code quality checking. A linter reads your code and flags style issues, potential bugs, and inconsistencies — like a spell-checker for code. Ruff is a very fast Python linter. | "We run ruff after every task to catch code quality issues before they accumulate." |
| Dependency (requirements.txt) | An external library your project needs to run. Listed in requirements.txt so anyone can install the same set. Like a recipe's ingredient list. | "Our requirements.txt pins specific versions of spaCy and pytest so the tool works consistently everywhere." |
