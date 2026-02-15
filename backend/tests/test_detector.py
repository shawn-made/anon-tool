"""Tests for the name/PII detection pipeline."""

from app.services.detector import (
    DetectedEntity,
    _deduplicate,
    _detect_ner,
    _detect_regex,
    _estimate_confidence,
    detect_entities,
)


# ---------------------------------------------------------------------------
# Regex detection tests
# ---------------------------------------------------------------------------


class TestRegexDetection:
    """Tests for email and phone regex detection."""

    def test_detect_email_simple(self):
        text = "Contact us at hello@example.com for details."
        entities = _detect_regex(text)
        assert len(entities) == 1
        assert entities[0].text == "hello@example.com"
        assert entities[0].entity_type == "EMAIL"
        assert entities[0].source == "regex"

    def test_detect_email_with_dots_and_plus(self):
        text = "Email john.doe+work@company.co.uk today."
        entities = _detect_regex(text)
        assert len(entities) == 1
        assert entities[0].text == "john.doe+work@company.co.uk"

    def test_detect_phone_parentheses(self):
        text = "Call (555) 123-4567 for support."
        entities = _detect_regex(text)
        phones = [e for e in entities if e.entity_type == "PHONE"]
        assert len(phones) == 1
        assert "555" in phones[0].text
        assert "4567" in phones[0].text

    def test_detect_phone_dashes(self):
        text = "Phone: 555-123-4567."
        entities = _detect_regex(text)
        phones = [e for e in entities if e.entity_type == "PHONE"]
        assert len(phones) == 1

    def test_detect_phone_dots(self):
        text = "Reach us at 555.123.4567."
        entities = _detect_regex(text)
        phones = [e for e in entities if e.entity_type == "PHONE"]
        assert len(phones) == 1

    def test_detect_multiple_emails(self):
        text = "Send to alice@a.com or bob@b.com."
        entities = _detect_regex(text)
        emails = [e for e in entities if e.entity_type == "EMAIL"]
        assert len(emails) == 2

    def test_no_regex_matches(self):
        text = "This text has no emails or phone numbers."
        entities = _detect_regex(text)
        assert len(entities) == 0

    def test_email_and_phone_together(self):
        text = "Contact sarah@example.com or (555) 987-6543."
        entities = _detect_regex(text)
        types = {e.entity_type for e in entities}
        assert "EMAIL" in types
        assert "PHONE" in types


# ---------------------------------------------------------------------------
# spaCy NER detection tests
# ---------------------------------------------------------------------------


class TestNerDetection:
    """Tests for spaCy NER-based person and organization detection."""

    def test_detect_person_multi_word(self):
        text = "John Smith attended the meeting."
        entities = _detect_ner(text)
        person_ents = [e for e in entities if e.entity_type == "PERSON"]
        assert any("John" in e.text for e in person_ents)

    def test_detect_organization(self):
        text = "She works at Google and previously was at Microsoft."
        entities = _detect_ner(text)
        org_ents = [e for e in entities if e.entity_type == "ORG"]
        assert len(org_ents) >= 1

    def test_detect_multiple_persons(self):
        text = "Alice Martinez and Bob Thompson discussed the proposal."
        entities = _detect_ner(text)
        person_ents = [e for e in entities if e.entity_type == "PERSON"]
        assert len(person_ents) >= 2

    def test_no_entities_in_plain_text(self):
        text = "The weather is sunny with clear skies."
        entities = _detect_ner(text)
        assert len(entities) == 0


# ---------------------------------------------------------------------------
# Confidence estimation tests
# ---------------------------------------------------------------------------


class TestConfidenceEstimation:
    """Tests for confidence scoring heuristics."""

    def test_multi_word_high_confidence(self):
        assert _estimate_confidence("John Smith") == 0.90

    def test_single_capitalized_medium(self):
        assert _estimate_confidence("Smith") == 0.80

    def test_single_lowercase_low(self):
        assert _estimate_confidence("something") == 0.60

    def test_three_word_name(self):
        assert _estimate_confidence("Mary Jane Watson") == 0.90


# ---------------------------------------------------------------------------
# Deduplication tests
# ---------------------------------------------------------------------------


class TestDeduplication:
    """Tests for overlapping entity deduplication."""

    def test_no_overlap(self):
        entities = [
            DetectedEntity("John", "PERSON", 0, 4, 0.80, "spacy"),
            DetectedEntity("Smith", "PERSON", 10, 15, 0.80, "spacy"),
        ]
        result = _deduplicate(entities)
        assert len(result) == 2

    def test_overlapping_prefers_longer(self):
        entities = [
            DetectedEntity("John", "PERSON", 0, 4, 0.80, "spacy"),
            DetectedEntity("John Smith", "PERSON", 0, 10, 0.90, "spacy"),
        ]
        result = _deduplicate(entities)
        assert len(result) == 1
        assert result[0].text == "John Smith"

    def test_empty_list(self):
        assert _deduplicate([]) == []

    def test_exact_overlap_keeps_higher_confidence(self):
        entities = [
            DetectedEntity("Acme Corp", "ORG", 5, 14, 0.90, "spacy"),
            DetectedEntity("Acme Corp", "ORG", 5, 14, 0.70, "spacy"),
        ]
        result = _deduplicate(entities)
        assert len(result) == 1
        assert result[0].confidence == 0.90


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------


class TestDetectEntities:
    """Integration tests for the full detection pipeline."""

    def test_simple_text(self, sample_text_simple):
        entities = detect_entities(sample_text_simple)
        texts = [e.text for e in entities]
        # Should detect at least one person name
        assert any("John" in t or "Jane" in t for t in texts)

    def test_mixed_text(self, sample_text_mixed):
        entities = detect_entities(sample_text_mixed)
        types = {e.entity_type for e in entities}
        # Should detect at least person names and email
        assert "EMAIL" in types or "PERSON" in types
        assert len(entities) >= 2

    def test_no_pii(self, sample_text_no_pii):
        entities = detect_entities(sample_text_no_pii)
        assert len(entities) == 0

    def test_business_email(self, sample_text_business_email):
        entities = detect_entities(sample_text_business_email)
        types = {e.entity_type for e in entities}
        # Should find emails
        assert "EMAIL" in types
        # Should find at least some person names
        assert any(e.entity_type == "PERSON" for e in entities)
        assert len(entities) >= 3

    def test_meeting_notes(self, sample_text_meeting_notes):
        entities = detect_entities(sample_text_meeting_notes)
        # Meeting notes have repeated names — after dedup, should still find unique ones
        person_ents = [e for e in entities if e.entity_type == "PERSON"]
        assert len(person_ents) >= 2

    def test_entities_sorted_by_position(self, sample_text_mixed):
        entities = detect_entities(sample_text_mixed)
        for i in range(len(entities) - 1):
            assert entities[i].start <= entities[i + 1].start

    def test_entity_offsets_match_text(self, sample_text_mixed):
        entities = detect_entities(sample_text_mixed)
        for ent in entities:
            assert sample_text_mixed[ent.start : ent.end] == ent.text

    def test_low_confidence_filtered(self):
        # A single lowercase word shouldn't pass the confidence filter
        text = "The project uses python for scripting."
        entities = detect_entities(text)
        for ent in entities:
            assert ent.confidence >= 0.65 or len(ent.text.split()) > 1

    def test_custom_min_confidence(self):
        text = "John Smith is the CEO."
        # With very high threshold, might filter some out
        high = detect_entities(text, min_confidence=0.95)
        low = detect_entities(text, min_confidence=0.50)
        assert len(low) >= len(high)
