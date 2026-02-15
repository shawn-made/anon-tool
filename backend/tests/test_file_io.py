"""Tests for file I/O anonymization and de-anonymization."""

from pathlib import Path

import pytest

from app.services.anonymizer import anonymize_file, deanonymize_file


class TestAnonymizeFile:
    """Tests for anonymize_file."""

    def test_anonymize_txt_file(self, tmp_path, tmp_anontool_dir):
        input_file = tmp_path / "test.txt"
        input_file.write_text("John Smith works at Acme Corporation.")
        output_file = tmp_path / "output.txt"

        result = anonymize_file(
            input_file,
            output_path=output_file,
            mapping_id="file-test",
            base_dir=tmp_anontool_dir,
        )

        assert Path(result["output_path"]).exists()
        content = Path(result["output_path"]).read_text()
        assert "John Smith" not in content
        assert result["entities_found"] >= 1

    def test_anonymize_md_file(self, tmp_path, tmp_anontool_dir):
        input_file = tmp_path / "notes.md"
        input_file.write_text("# Meeting\nAlice Martinez presented the results.")
        output_file = tmp_path / "output.md"

        result = anonymize_file(
            input_file,
            output_path=output_file,
            mapping_id="md-test",
            base_dir=tmp_anontool_dir,
        )

        assert Path(result["output_path"]).exists()

    def test_auto_generate_output_path(self, tmp_path, tmp_anontool_dir):
        input_file = tmp_path / "report.txt"
        input_file.write_text("Bob Thompson filed the report.")

        result = anonymize_file(
            input_file,
            mapping_id="auto-out",
            base_dir=tmp_anontool_dir,
        )

        assert "report.anon.txt" in result["output_path"]

    def test_auto_generate_mapping_id(self, tmp_path, tmp_anontool_dir):
        input_file = tmp_path / "memo.txt"
        input_file.write_text("Carol Davis sent the memo.")

        result = anonymize_file(
            input_file,
            output_path=tmp_path / "out.txt",
            base_dir=tmp_anontool_dir,
        )

        assert result["mapping_id"].startswith("memo_")

    def test_preserves_original_file(self, tmp_path, tmp_anontool_dir):
        original_text = "John Smith is the manager."
        input_file = tmp_path / "original.txt"
        input_file.write_text(original_text)

        anonymize_file(
            input_file,
            output_path=tmp_path / "out.txt",
            mapping_id="preserve-test",
            base_dir=tmp_anontool_dir,
        )

        assert input_file.read_text() == original_text

    def test_file_not_found(self, tmp_path, tmp_anontool_dir):
        with pytest.raises(FileNotFoundError):
            anonymize_file(
                tmp_path / "nonexistent.txt",
                mapping_id="nf-test",
                base_dir=tmp_anontool_dir,
            )

    def test_unsupported_extension(self, tmp_path, tmp_anontool_dir):
        input_file = tmp_path / "data.csv"
        input_file.write_text("name,email\nJohn,john@a.com")

        with pytest.raises(ValueError, match="Unsupported"):
            anonymize_file(
                input_file,
                mapping_id="ext-test",
                base_dir=tmp_anontool_dir,
            )


class TestDeanonymizeFile:
    """Tests for deanonymize_file."""

    def test_deanonymize_file(self, tmp_path, tmp_anontool_dir):
        # First anonymize
        original_text = "John Smith met with Jane Doe."
        input_file = tmp_path / "original.txt"
        input_file.write_text(original_text)
        anon_output = tmp_path / "anon.txt"

        anonymize_file(
            input_file,
            output_path=anon_output,
            mapping_id="deanon-test",
            base_dir=tmp_anontool_dir,
        )

        # Then de-anonymize
        restored_output = tmp_path / "restored.txt"
        deanonymize_file(
            anon_output,
            mapping_id="deanon-test",
            output_path=restored_output,
            base_dir=tmp_anontool_dir,
        )

        restored = restored_output.read_text()
        assert restored == original_text

    def test_auto_output_path_strips_anon(self, tmp_path, tmp_anontool_dir):
        input_file = tmp_path / "report.anon.txt"
        input_file.write_text("Person_A went to the store.")

        # Create an empty mapping so it doesn't crash
        from app.services.mapping_store import MappingStore

        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("strip-test")
        store.save()

        result = deanonymize_file(
            input_file,
            mapping_id="strip-test",
            base_dir=tmp_anontool_dir,
        )

        assert "report.restored.txt" in result["output_path"]


class TestFileRoundTrip:
    """End-to-end file round-trip tests."""

    def test_full_round_trip(self, tmp_path, tmp_anontool_dir):
        original_text = (
            "Dear James Wilson,\n\n"
            "Thank you for contacting Acme Corporation. "
            "Your case has been assigned to Sarah Johnson (sarah.johnson@acme.com). "
            "Please call (555) 123-4567.\n\n"
            "Best regards,\nMichael Chen"
        )
        input_file = tmp_path / "letter.txt"
        input_file.write_text(original_text)

        # Anonymize
        anon_output = tmp_path / "letter.anon.txt"
        anonymize_file(
            input_file,
            output_path=anon_output,
            mapping_id="roundtrip",
            base_dir=tmp_anontool_dir,
        )

        anon_content = anon_output.read_text()
        assert "James Wilson" not in anon_content
        assert "sarah.johnson@acme.com" not in anon_content

        # De-anonymize
        restored_output = tmp_path / "letter.restored.txt"
        deanonymize_file(
            anon_output,
            mapping_id="roundtrip",
            output_path=restored_output,
            base_dir=tmp_anontool_dir,
        )

        assert restored_output.read_text() == original_text
