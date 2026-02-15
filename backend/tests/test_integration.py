"""End-to-end integration tests for AnonTool."""

from __future__ import annotations

from pathlib import Path

from app.services.anonymizer import (
    anonymize_file,
    anonymize_text,
    deanonymize_file,
)
from app.services.mapping_store import MappingStore

SAMPLES_DIR = Path(__file__).parent / "samples"


class TestSampleDocumentRoundTrips:
    """Verify full round-trip on all 3 sample documents."""

    def test_business_email_round_trip(self, tmp_path, tmp_anontool_dir):
        input_file = SAMPLES_DIR / "business_email.txt"
        original = input_file.read_text()
        anon_file = tmp_path / "business_email.anon.txt"
        restored_file = tmp_path / "business_email.restored.txt"

        # Anonymize
        anon_result = anonymize_file(
            input_file,
            output_path=anon_file,
            mapping_id="integ-biz",
            base_dir=tmp_anontool_dir,
        )
        anon_content = anon_file.read_text()

        # Verify real names are removed
        assert "Robert Garcia" not in anon_content
        assert "Lisa Wang" not in anon_content
        assert "robert.garcia@techstart.io" not in anon_content
        assert anon_result["entities_found"] >= 3

        # De-anonymize
        deanonymize_file(
            anon_file,
            mapping_id="integ-biz",
            output_path=restored_file,
            base_dir=tmp_anontool_dir,
        )

        assert restored_file.read_text() == original

    def test_meeting_notes_round_trip(self, tmp_path, tmp_anontool_dir):
        input_file = SAMPLES_DIR / "meeting_notes.txt"
        original = input_file.read_text()
        anon_file = tmp_path / "meeting_notes.anon.txt"
        restored_file = tmp_path / "meeting_notes.restored.txt"

        anon_result = anonymize_file(
            input_file,
            output_path=anon_file,
            mapping_id="integ-meeting",
            base_dir=tmp_anontool_dir,
        )
        anon_content = anon_file.read_text()

        # Verify names are removed
        assert "Alice Martinez" not in anon_content
        assert "Bob Thompson" not in anon_content
        assert anon_result["entities_found"] >= 4

        # De-anonymize
        deanonymize_file(
            anon_file,
            mapping_id="integ-meeting",
            output_path=restored_file,
            base_dir=tmp_anontool_dir,
        )

        assert restored_file.read_text() == original

    def test_project_report_round_trip(self, tmp_path, tmp_anontool_dir):
        input_file = SAMPLES_DIR / "project_report.txt"
        original = input_file.read_text()
        anon_file = tmp_path / "project_report.anon.txt"
        restored_file = tmp_path / "project_report.restored.txt"

        anon_result = anonymize_file(
            input_file,
            output_path=anon_file,
            mapping_id="integ-report",
            base_dir=tmp_anontool_dir,
        )
        anon_content = anon_file.read_text()

        # Verify names are removed
        assert "Elena Rodriguez" not in anon_content
        assert "Thomas Wright" not in anon_content
        assert anon_result["entities_found"] >= 5

        # De-anonymize
        deanonymize_file(
            anon_file,
            mapping_id="integ-report",
            output_path=restored_file,
            base_dir=tmp_anontool_dir,
        )

        assert restored_file.read_text() == original


class TestMappingPersistence:
    """Verify that shared mappings produce consistent pseudonyms across files."""

    def test_shared_mapping_across_files(self, tmp_path, tmp_anontool_dir):
        # File A mentions Robert Garcia and Lisa Wang
        file_a = tmp_path / "file_a.txt"
        file_a.write_text(
            "Robert Garcia scheduled a meeting with Lisa Wang."
        )

        # File B mentions Robert Garcia and a new person
        file_b = tmp_path / "file_b.txt"
        file_b.write_text(
            "Robert Garcia met with David Park to discuss the project."
        )

        # Anonymize both with the same mapping
        anonymize_file(
            file_a,
            output_path=tmp_path / "a.anon.txt",
            mapping_id="shared-map",
            base_dir=tmp_anontool_dir,
        )
        anonymize_file(
            file_b,
            output_path=tmp_path / "b.anon.txt",
            mapping_id="shared-map",
            base_dir=tmp_anontool_dir,
        )

        # Load the mapping and verify Robert Garcia has the same pseudonym
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("shared-map")
        entries = store.get_entries()

        # Robert Garcia should appear once in the mapping
        if "Robert Garcia" in entries:
            pseudonym = entries["Robert Garcia"]["pseudonym"]
            # Both output files should contain the same pseudonym
            a_content = (tmp_path / "a.anon.txt").read_text()
            b_content = (tmp_path / "b.anon.txt").read_text()
            assert pseudonym in a_content
            assert pseudonym in b_content

    def test_mapping_survives_reload(self, tmp_anontool_dir):
        # Anonymize text, which saves the mapping
        text = "John Smith and Jane Doe work together."
        anonymize_text(text, "reload-test", base_dir=tmp_anontool_dir)

        # Create a fresh store and load the same mapping
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("reload-test")
        entries = store.get_entries()

        # Verify entries persisted
        assert len(entries) >= 1


class TestOutputVerification:
    """Additional checks on anonymized output quality."""

    def test_no_real_names_in_anonymized_business_email(
        self, tmp_anontool_dir
    ):
        input_file = SAMPLES_DIR / "business_email.txt"
        text = input_file.read_text()
        result = anonymize_text(text, "verify-biz", base_dir=tmp_anontool_dir)

        real_names = [
            "Robert Garcia",
            "Lisa Wang",
            "David Park",
            "Michael Chen",
        ]
        for name in real_names:
            assert name not in result.anonymized_text

    def test_no_real_emails_in_anonymized_output(self, tmp_anontool_dir):
        input_file = SAMPLES_DIR / "business_email.txt"
        text = input_file.read_text()
        result = anonymize_text(
            text, "verify-emails", base_dir=tmp_anontool_dir
        )

        real_emails = [
            "robert.garcia@techstart.io",
            "lisa.wang@globalfinance.com",
            "david.park@techstart.io",
        ]
        for email in real_emails:
            assert email not in result.anonymized_text

    def test_pseudonyms_are_consistent_format(self, tmp_anontool_dir):
        text = "John Smith and Jane Doe from Acme Corp contacted bob@test.com."
        anonymize_text(text, "format-check", base_dir=tmp_anontool_dir)

        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("format-check")
        entries = store.get_entries()

        for info in entries.values():
            pseudonym = info["pseudonym"]
            etype = info["type"]
            if etype == "PERSON":
                assert pseudonym.startswith("Person_")
            elif etype == "ORG":
                assert pseudonym.startswith("Company_")
            elif etype == "EMAIL":
                assert pseudonym.startswith("Email_")
            elif etype == "PHONE":
                assert pseudonym.startswith("Phone_")
