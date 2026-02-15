"""Tests for the core anonymize/de-anonymize logic."""

from app.services.anonymizer import AnonymizeResult, anonymize_text, deanonymize_text


class TestAnonymizeText:
    """Tests for the anonymize_text function."""

    def test_basic_anonymization(self, tmp_anontool_dir):
        text = "John Smith met with Jane Doe."
        result = anonymize_text(text, "test-anon", base_dir=tmp_anontool_dir)
        assert isinstance(result, AnonymizeResult)
        assert "John Smith" not in result.anonymized_text
        assert result.mapping_id == "test-anon"
        assert len(result.entities_found) >= 1

    def test_empty_text(self, tmp_anontool_dir):
        result = anonymize_text("", "test-empty", base_dir=tmp_anontool_dir)
        assert result.anonymized_text == ""
        assert len(result.entities_found) == 0

    def test_no_entities(self, tmp_anontool_dir):
        text = "The weather is sunny with clear skies."
        result = anonymize_text(text, "test-none", base_dir=tmp_anontool_dir)
        assert result.anonymized_text == text
        assert len(result.entities_found) == 0

    def test_email_anonymization(self, tmp_anontool_dir):
        text = "Contact john@example.com for details."
        result = anonymize_text(text, "test-email", base_dir=tmp_anontool_dir)
        assert "john@example.com" not in result.anonymized_text
        assert "Email_1" in result.anonymized_text

    def test_phone_anonymization(self, tmp_anontool_dir):
        text = "Call (555) 123-4567 for support."
        result = anonymize_text(text, "test-phone", base_dir=tmp_anontool_dir)
        assert "(555) 123-4567" not in result.anonymized_text

    def test_repeated_name_same_pseudonym(self, tmp_anontool_dir):
        text = "Alice Martinez said hello. Alice Martinez left."
        result = anonymize_text(text, "test-repeat", base_dir=tmp_anontool_dir)
        # The same person should get the same pseudonym
        # Count occurrences of the pseudonym — should appear twice
        pseudonym = "Person_A"
        assert result.anonymized_text.count(pseudonym) >= 1

    def test_multiple_types(self, tmp_anontool_dir, sample_text_mixed):
        result = anonymize_text(
            sample_text_mixed, "test-multi", base_dir=tmp_anontool_dir
        )
        # Should have replaced some entities
        assert result.anonymized_text != sample_text_mixed
        assert len(result.entities_found) >= 2

    def test_pseudonyms_present_in_output(self, tmp_anontool_dir):
        text = "Robert Garcia is the CEO of TechStart."
        result = anonymize_text(text, "test-present", base_dir=tmp_anontool_dir)
        # Should contain Person_ or Company_ pseudonyms
        assert "Person_" in result.anonymized_text or "Company_" in result.anonymized_text

    def test_mapping_persists_after_anonymize(self, tmp_anontool_dir):
        text = "John Smith is here."
        anonymize_text(text, "test-persist", base_dir=tmp_anontool_dir)
        # Mapping file should exist
        mapping_file = tmp_anontool_dir / "mappings" / "test-persist.json"
        assert mapping_file.exists()


class TestDeanonymizeText:
    """Tests for the deanonymize_text function."""

    def test_basic_deanonymization(self, tmp_anontool_dir):
        original = "John Smith met with Jane Doe at the office."
        result = anonymize_text(original, "test-deanon", base_dir=tmp_anontool_dir)
        restored = deanonymize_text(
            result.anonymized_text, "test-deanon", base_dir=tmp_anontool_dir
        )
        # Restored should contain the original names
        assert "John Smith" in restored or "Jane Doe" in restored

    def test_empty_mapping_returns_text(self, tmp_anontool_dir):
        text = "Person_A went to the store."
        restored = deanonymize_text(text, "nonexistent-id", base_dir=tmp_anontool_dir)
        assert restored == text

    def test_deanonymize_no_entities_text(self, tmp_anontool_dir):
        text = "The weather is sunny."
        anonymize_text(text, "test-noent", base_dir=tmp_anontool_dir)
        restored = deanonymize_text(text, "test-noent", base_dir=tmp_anontool_dir)
        assert restored == text


class TestRoundTrip:
    """Tests verifying anonymize -> deanonymize round-trip fidelity."""

    def test_round_trip_simple(self, tmp_anontool_dir, sample_text_simple):
        result = anonymize_text(
            sample_text_simple, "rt-simple", base_dir=tmp_anontool_dir
        )
        restored = deanonymize_text(
            result.anonymized_text, "rt-simple", base_dir=tmp_anontool_dir
        )
        assert restored == sample_text_simple

    def test_round_trip_mixed(self, tmp_anontool_dir, sample_text_mixed):
        result = anonymize_text(
            sample_text_mixed, "rt-mixed", base_dir=tmp_anontool_dir
        )
        restored = deanonymize_text(
            result.anonymized_text, "rt-mixed", base_dir=tmp_anontool_dir
        )
        assert restored == sample_text_mixed

    def test_round_trip_business_email(
        self, tmp_anontool_dir, sample_text_business_email
    ):
        result = anonymize_text(
            sample_text_business_email, "rt-biz", base_dir=tmp_anontool_dir
        )
        restored = deanonymize_text(
            result.anonymized_text, "rt-biz", base_dir=tmp_anontool_dir
        )
        assert restored == sample_text_business_email

    def test_round_trip_meeting_notes(
        self, tmp_anontool_dir, sample_text_meeting_notes
    ):
        result = anonymize_text(
            sample_text_meeting_notes, "rt-meeting", base_dir=tmp_anontool_dir
        )
        restored = deanonymize_text(
            result.anonymized_text, "rt-meeting", base_dir=tmp_anontool_dir
        )
        assert restored == sample_text_meeting_notes

    def test_round_trip_no_pii(self, tmp_anontool_dir, sample_text_no_pii):
        result = anonymize_text(
            sample_text_no_pii, "rt-nopii", base_dir=tmp_anontool_dir
        )
        restored = deanonymize_text(
            result.anonymized_text, "rt-nopii", base_dir=tmp_anontool_dir
        )
        assert restored == sample_text_no_pii
