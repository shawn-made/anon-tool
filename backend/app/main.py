"""CLI entry point for AnonTool."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ANSI color codes for terminal output
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_RED = "\033[31m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _color(text: str, code: str) -> str:
    """Wrap text in ANSI color codes."""
    return f"{code}{text}{_RESET}"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="anontool",
        description="Local file anonymization/de-anonymization tool powered by spaCy NER.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # anonymize
    anon = subparsers.add_parser(
        "anonymize",
        help="Anonymize a file by replacing names with pseudonyms",
    )
    anon.add_argument("input_file", help="Path to the file to anonymize")
    anon.add_argument(
        "--mapping-id", help="Mapping ID to use (auto-generated if omitted)"
    )
    anon.add_argument("--output", help="Output file path (auto-generated if omitted)")
    anon.add_argument(
        "--use-ollama",
        action="store_true",
        help="Use Ollama LLM for enhanced entity verification",
    )

    # deanonymize
    deanon = subparsers.add_parser(
        "deanonymize",
        help="Restore anonymized file using a mapping",
    )
    deanon.add_argument("input_file", help="Path to the anonymized file")
    deanon.add_argument(
        "--mapping-id", required=True, help="Mapping ID used during anonymization"
    )
    deanon.add_argument(
        "--output", help="Output file path (auto-generated if omitted)"
    )

    # list-mappings
    subparsers.add_parser(
        "list-mappings",
        help="List all available mapping IDs",
    )

    # show-mapping
    show = subparsers.add_parser(
        "show-mapping",
        help="Display a mapping's contents",
    )
    show.add_argument("mapping_id", help="The mapping ID to display")

    return parser


def cmd_anonymize(args: argparse.Namespace) -> int:
    """Handle the anonymize subcommand."""
    from app.services.anonymizer import anonymize_file

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(_color(f"Error: File not found: {input_path}", _RED), file=sys.stderr)
        return 1

    try:
        result = anonymize_file(
            input_path=input_path,
            output_path=args.output,
            mapping_id=args.mapping_id,
            use_ollama=args.use_ollama,
        )
    except ValueError as e:
        print(_color(f"Error: {e}", _RED), file=sys.stderr)
        return 1

    print(_color("Anonymization complete!", _GREEN))
    print(f"  Entities found: {_color(str(result['entities_found']), _CYAN)}")
    print(f"  Output file:    {_color(result['output_path'], _CYAN)}")
    print(f"  Mapping ID:     {_color(result['mapping_id'], _YELLOW)}")

    if args.use_ollama:
        try:
            from app.services.ollama_client import OllamaClient

            client = OllamaClient()
            if not client.is_available():
                print(
                    _color(
                        "  Note: Ollama not running — used spaCy-only detection",
                        _YELLOW,
                    )
                )
        except Exception:
            pass

    return 0


def cmd_deanonymize(args: argparse.Namespace) -> int:
    """Handle the deanonymize subcommand."""
    from app.services.anonymizer import deanonymize_file

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(_color(f"Error: File not found: {input_path}", _RED), file=sys.stderr)
        return 1

    mapping_path = Path.home() / ".anontool" / "mappings" / f"{args.mapping_id}.json"
    if not mapping_path.exists():
        print(
            _color(f"Error: Mapping not found: {args.mapping_id}", _RED),
            file=sys.stderr,
        )
        print(
            f"  Available mappings: run {_color('anontool list-mappings', _CYAN)}",
            file=sys.stderr,
        )
        return 1

    result = deanonymize_file(
        input_path=input_path,
        mapping_id=args.mapping_id,
        output_path=args.output,
    )

    print(_color("De-anonymization complete!", _GREEN))
    print(f"  Output file: {_color(result['output_path'], _CYAN)}")
    print(f"  Mapping ID:  {_color(result['mapping_id'], _YELLOW)}")

    return 0


def cmd_list_mappings() -> int:
    """Handle the list-mappings subcommand."""
    from app.services.mapping_store import MappingStore

    store = MappingStore()
    mappings = store.list_mappings()

    if not mappings:
        print("No mappings found.")
        return 0

    print(_color(f"Found {len(mappings)} mapping(s):", _BOLD))
    for mid in mappings:
        print(f"  - {_color(mid, _CYAN)}")

    return 0


def cmd_show_mapping(args: argparse.Namespace) -> int:
    """Handle the show-mapping subcommand."""
    mapping_path = Path.home() / ".anontool" / "mappings" / f"{args.mapping_id}.json"

    if not mapping_path.exists():
        print(
            _color(f"Error: Mapping not found: {args.mapping_id}", _RED),
            file=sys.stderr,
        )
        return 1

    with open(mapping_path) as f:
        data = json.load(f)

    print(_color(f"Mapping: {data['mapping_id']}", _BOLD))
    print(f"  Created: {data.get('created', 'unknown')}")
    print(f"  Updated: {data.get('updated', 'unknown')}")
    entries = data.get("entries", {})
    print(f"  Entries: {_color(str(len(entries)), _CYAN)}")

    if entries:
        print()
        print(f"  {'Real Name':<30} {'Pseudonym':<20} {'Type'}")
        print(f"  {'-' * 30} {'-' * 20} {'-' * 10}")
        for real_name, info in entries.items():
            print(
                f"  {real_name:<30} "
                f"{_color(info['pseudonym'], _YELLOW):<29} "
                f"{info['type']}"
            )

    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    commands = {
        "anonymize": lambda: cmd_anonymize(args),
        "deanonymize": lambda: cmd_deanonymize(args),
        "list-mappings": lambda: cmd_list_mappings(),
        "show-mapping": lambda: cmd_show_mapping(args),
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler()


if __name__ == "__main__":
    sys.exit(main())
