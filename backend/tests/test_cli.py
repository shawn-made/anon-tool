"""CLI integration tests using subprocess."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run the CLI as a subprocess."""
    cmd = [sys.executable, "-m", "app.main", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or str(Path(__file__).parent.parent),
    )


class TestCLIHelp:
    """Tests for --help output."""

    def test_main_help(self):
        result = run_cli("--help")
        assert result.returncode == 0
        assert "anonymize" in result.stdout
        assert "deanonymize" in result.stdout
        assert "list-mappings" in result.stdout
        assert "show-mapping" in result.stdout

    def test_anonymize_help(self):
        result = run_cli("anonymize", "--help")
        assert result.returncode == 0
        assert "input_file" in result.stdout
        assert "--mapping-id" in result.stdout
        assert "--use-ollama" in result.stdout

    def test_deanonymize_help(self):
        result = run_cli("deanonymize", "--help")
        assert result.returncode == 0
        assert "input_file" in result.stdout
        assert "--mapping-id" in result.stdout

    def test_no_command_shows_help(self):
        result = run_cli()
        assert result.returncode == 1


class TestCLIAnonymize:
    """Tests for the anonymize subcommand."""

    def test_anonymize_file(self, tmp_path):
        input_file = tmp_path / "test.txt"
        input_file.write_text("John Smith works at Acme Corporation.")
        output_file = tmp_path / "out.txt"

        result = run_cli(
            "anonymize",
            str(input_file),
            "--mapping-id", "cli-test",
            "--output", str(output_file),
        )

        assert result.returncode == 0
        assert "Anonymization complete" in result.stdout
        assert output_file.exists()
        content = output_file.read_text()
        assert "John Smith" not in content

    def test_anonymize_file_not_found(self):
        result = run_cli("anonymize", "/tmp/nonexistent_file_xyz.txt")
        assert result.returncode == 1
        assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()

    def test_anonymize_unsupported_format(self, tmp_path):
        input_file = tmp_path / "data.csv"
        input_file.write_text("name\nJohn")

        result = run_cli(
            "anonymize",
            str(input_file),
            "--mapping-id", "csv-test",
        )

        assert result.returncode == 1


class TestCLIDeanonymize:
    """Tests for the deanonymize subcommand."""

    def test_deanonymize_round_trip(self, tmp_path):
        # First anonymize
        input_file = tmp_path / "original.txt"
        original = "John Smith met with Jane Doe at the office."
        input_file.write_text(original)
        anon_file = tmp_path / "anon.txt"

        run_cli(
            "anonymize",
            str(input_file),
            "--mapping-id", "cli-rt",
            "--output", str(anon_file),
        )

        # Then deanonymize
        restored_file = tmp_path / "restored.txt"
        result = run_cli(
            "deanonymize",
            str(anon_file),
            "--mapping-id", "cli-rt",
            "--output", str(restored_file),
        )

        assert result.returncode == 0
        assert "De-anonymization complete" in result.stdout
        assert restored_file.read_text() == original

    def test_deanonymize_missing_mapping(self, tmp_path):
        input_file = tmp_path / "anon.txt"
        input_file.write_text("Person_A went to the store.")

        result = run_cli(
            "deanonymize",
            str(input_file),
            "--mapping-id", "nonexistent-mapping-xyz",
        )

        assert result.returncode == 1
        assert "not found" in result.stderr.lower()


class TestCLIListMappings:
    """Tests for the list-mappings subcommand."""

    def test_list_mappings(self):
        result = run_cli("list-mappings")
        assert result.returncode == 0
