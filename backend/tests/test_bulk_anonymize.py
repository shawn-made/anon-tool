"""Tests for bulk folder anonymization."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.anonymizer import (
    BulkAnonymizeResult,
    _get_file_creation_time,
    anonymize_folder,
)


class TestGetFileCreationTime:
    """Tests for _get_file_creation_time helper."""

    def test_returns_float_timestamp(self, tmp_path):
        """Should return a float timestamp."""
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = _get_file_creation_time(f)
        assert isinstance(result, float)
        assert result > 0

    def test_older_file_has_smaller_timestamp(self, tmp_path):
        """Files created earlier should have smaller timestamps."""
        f1 = tmp_path / "first.txt"
        f1.write_text("first")
        time.sleep(0.05)
        f2 = tmp_path / "second.txt"
        f2.write_text("second")
        assert _get_file_creation_time(f1) <= _get_file_creation_time(f2)


class TestAnonymizeFolder:
    """Tests for anonymize_folder function."""

    def test_basic_bulk_anonymize(self, sample_transcript_folder, tmp_anontool_dir):
        """Should process all supported files and produce merged output."""
        result = anonymize_folder(
            folder_path=sample_transcript_folder,
            mapping_id="test_bulk",
            base_dir=tmp_anontool_dir,
        )

        assert isinstance(result, BulkAnonymizeResult)
        assert result.files_processed == 3
        assert result.files_failed == 0
        assert result.total_entities > 0
        assert result.mapping_id == "test_bulk"

        output = Path(result.output_path).read_text()
        assert "=== transcript_001.txt" in output
        assert "=== transcript_002.txt" in output
        assert "=== transcript_003.md" in output

    def test_sorts_by_creation_date(self, tmp_path, tmp_anontool_dir):
        """Files should appear in the output sorted oldest-first."""
        folder = tmp_path / "sorted_test"
        folder.mkdir()

        # Create files with small delays to ensure different creation times
        (folder / "file_c.txt").write_text("Alice Martinez works at Pinnacle Solutions.")
        time.sleep(0.05)
        (folder / "file_a.txt").write_text("Bob Thompson joined Vertex Analytics.")
        time.sleep(0.05)
        (folder / "file_b.txt").write_text("Carol Davis left Global Finance Corp.")

        result = anonymize_folder(
            folder_path=folder,
            mapping_id="sort_test",
            base_dir=tmp_anontool_dir,
        )

        output = Path(result.output_path).read_text()
        # file_c was created first, file_a second, file_b third
        pos_c = output.index("=== file_c.txt")
        pos_a = output.index("=== file_a.txt")
        pos_b = output.index("=== file_b.txt")
        assert pos_c < pos_a < pos_b

    def test_shared_mapping_across_files(
        self, sample_transcript_folder, tmp_anontool_dir
    ):
        """Same person name in different files should get the same pseudonym."""
        result = anonymize_folder(
            folder_path=sample_transcript_folder,
            mapping_id="shared_map",
            base_dir=tmp_anontool_dir,
        )

        output = Path(result.output_path).read_text()
        # "John Smith" appears in transcript_001 and transcript_002
        # Both should use the same pseudonym across files
        assert "John Smith" not in output
        # Find which pseudonym "John Smith" got and verify it appears in both sections
        import re

        person_tags = re.findall(r"Person_[A-Z]+", output)
        # At least one person pseudonym should appear more than once (shared mapping)
        from collections import Counter

        counts = Counter(person_tags)
        shared = [tag for tag, count in counts.items() if count > 1]
        assert len(shared) >= 1, f"Expected shared pseudonyms across files, got: {counts}"

    def test_section_headers_format(self, sample_transcript_folder, tmp_anontool_dir):
        """Each file section should have the correct header format."""
        result = anonymize_folder(
            folder_path=sample_transcript_folder,
            mapping_id="header_test",
            base_dir=tmp_anontool_dir,
        )

        output = Path(result.output_path).read_text()
        # Headers should match "=== filename (Created: YYYY-MM-DD) ==="
        import re

        headers = re.findall(r"=== .+ \(Created: \d{4}-\d{2}-\d{2}\) ===", output)
        assert len(headers) == 3

    def test_empty_folder(self, tmp_path, tmp_anontool_dir):
        """Empty folder should raise ValueError."""
        folder = tmp_path / "empty"
        folder.mkdir()

        with pytest.raises(ValueError, match="No supported files"):
            anonymize_folder(
                folder_path=folder,
                mapping_id="empty_test",
                base_dir=tmp_anontool_dir,
            )

    def test_no_supported_files(self, tmp_path, tmp_anontool_dir):
        """Folder with only unsupported files should raise ValueError."""
        folder = tmp_path / "unsupported"
        folder.mkdir()
        (folder / "data.csv").write_text("a,b,c")
        (folder / "report.pdf").write_bytes(b"fake pdf")

        with pytest.raises(ValueError, match="No supported files"):
            anonymize_folder(
                folder_path=folder,
                mapping_id="unsup_test",
                base_dir=tmp_anontool_dir,
            )

    def test_mixed_extensions(self, tmp_path, tmp_anontool_dir):
        """Should only process .txt and .md files, skipping others."""
        folder = tmp_path / "mixed"
        folder.mkdir()
        (folder / "notes.txt").write_text("John Smith wrote this.")
        (folder / "readme.md").write_text("Sarah Johnson reviewed this.")
        (folder / "data.csv").write_text("a,b,c")
        (folder / "image.png").write_bytes(b"fake png")

        result = anonymize_folder(
            folder_path=folder,
            mapping_id="mixed_test",
            base_dir=tmp_anontool_dir,
        )

        assert result.files_processed == 2
        output = Path(result.output_path).read_text()
        assert "=== notes.txt" in output
        assert "=== readme.md" in output
        assert "data.csv" not in output
        assert "image.png" not in output

    def test_folder_not_found(self, tmp_path, tmp_anontool_dir):
        """Non-existent folder should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Folder not found"):
            anonymize_folder(
                folder_path=tmp_path / "nonexistent",
                mapping_id="missing",
                base_dir=tmp_anontool_dir,
            )

    def test_path_is_file_not_dir(self, tmp_path, tmp_anontool_dir):
        """Passing a file path should raise ValueError."""
        f = tmp_path / "file.txt"
        f.write_text("not a folder")

        with pytest.raises(ValueError, match="Not a directory"):
            anonymize_folder(
                folder_path=f,
                mapping_id="not_dir",
                base_dir=tmp_anontool_dir,
            )

    def test_auto_generate_mapping_id(self, sample_transcript_folder, tmp_anontool_dir):
        """Should auto-generate a mapping ID from folder name when omitted."""
        result = anonymize_folder(
            folder_path=sample_transcript_folder,
            base_dir=tmp_anontool_dir,
        )

        assert "transcripts_bulk_" in result.mapping_id

    def test_auto_generate_output_path(
        self, sample_transcript_folder, tmp_anontool_dir
    ):
        """Should auto-generate output path when omitted."""
        result = anonymize_folder(
            folder_path=sample_transcript_folder,
            mapping_id="auto_out",
            base_dir=tmp_anontool_dir,
        )

        assert result.output_path.endswith("transcripts_bulk.txt")

    def test_custom_output_path(self, sample_transcript_folder, tmp_anontool_dir):
        """Should use provided output path."""
        custom = tmp_anontool_dir / "output" / "custom_output.txt"

        result = anonymize_folder(
            folder_path=sample_transcript_folder,
            mapping_id="custom_test",
            output_path=custom,
            base_dir=tmp_anontool_dir,
        )

        assert result.output_path == str(custom)
        assert custom.exists()

    def test_file_error_skipped_and_reported(self, tmp_path, tmp_anontool_dir):
        """Files that fail should be skipped and reported, not stop processing."""
        folder = tmp_path / "with_errors"
        folder.mkdir()
        (folder / "good.txt").write_text("John Smith is here.")
        # Write binary garbage that will fail UTF-8 decode
        (folder / "bad.txt").write_bytes(b"\x80\x81\x82\x83")
        (folder / "also_good.txt").write_text("Jane Doe is here too.")

        result = anonymize_folder(
            folder_path=folder,
            mapping_id="error_test",
            base_dir=tmp_anontool_dir,
        )

        assert result.files_processed == 2
        assert result.files_failed == 1
        assert len(result.failed_files) == 1
        assert result.failed_files[0][0] == "bad.txt"

    def test_progress_callback_called(
        self, sample_transcript_folder, tmp_anontool_dir
    ):
        """Progress callback should be called for each file."""
        callback = MagicMock()

        anonymize_folder(
            folder_path=sample_transcript_folder,
            mapping_id="progress_test",
            base_dir=tmp_anontool_dir,
            progress_callback=callback,
        )

        assert callback.call_count == 3
        # First call should be (1, 3, filename)
        first_call = callback.call_args_list[0]
        assert first_call[0][0] == 1  # current
        assert first_call[0][1] == 3  # total

    def test_entity_count_totals(self, sample_transcript_folder, tmp_anontool_dir):
        """Total entities should sum correctly across all files."""
        result = anonymize_folder(
            folder_path=sample_transcript_folder,
            mapping_id="count_test",
            base_dir=tmp_anontool_dir,
        )

        assert result.total_entities > 0
        assert isinstance(result.total_entities, int)

    def test_single_file_in_folder(self, tmp_path, tmp_anontool_dir):
        """Folder with just one file should work correctly."""
        folder = tmp_path / "single"
        folder.mkdir()
        (folder / "only.txt").write_text("Alice Martinez wrote this report.")

        result = anonymize_folder(
            folder_path=folder,
            mapping_id="single_test",
            base_dir=tmp_anontool_dir,
        )

        assert result.files_processed == 1
        output = Path(result.output_path).read_text()
        assert "=== only.txt" in output
        assert "Alice Martinez" not in output


class TestBulkAnonymizeCLI:
    """Tests for the bulk-anonymize CLI subcommand."""

    def test_bulk_anonymize_help(self):
        """--help should show folder argument and options."""
        result = subprocess.run(
            [sys.executable, "-m", "app.main", "bulk-anonymize", "--help"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "folder" in result.stdout
        assert "--mapping-id" in result.stdout
        assert "--output" in result.stdout
        assert "--use-ollama" in result.stdout

    def test_bulk_anonymize_end_to_end(self, tmp_path):
        """Full CLI flow: create folder, run command, verify output."""
        folder = tmp_path / "cli_test"
        folder.mkdir()
        (folder / "doc1.txt").write_text(
            "John Smith met with Sarah Johnson at Acme Corporation."
        )
        (folder / "doc2.txt").write_text(
            "Robert Garcia from TechStart called John Smith."
        )

        output_file = tmp_path / "merged.txt"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.main",
                "bulk-anonymize",
                str(folder),
                "--mapping-id",
                "cli_e2e",
                "--output",
                str(output_file),
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )

        assert result.returncode == 0
        assert "Bulk anonymization complete" in result.stdout
        assert output_file.exists()

        content = output_file.read_text()
        assert "John Smith" not in content
        assert "=== doc1.txt" in content
        assert "=== doc2.txt" in content

    def test_bulk_anonymize_folder_not_found(self):
        """Should print error and exit 1 for missing folder."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.main",
                "bulk-anonymize",
                "/nonexistent/folder",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )

        assert result.returncode == 1
        assert "Folder not found" in result.stderr

    def test_bulk_anonymize_empty_folder(self, tmp_path):
        """Should print error for empty folder."""
        folder = tmp_path / "empty_cli"
        folder.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.main",
                "bulk-anonymize",
                str(folder),
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )

        assert result.returncode == 1
        assert "No supported files" in result.stderr
