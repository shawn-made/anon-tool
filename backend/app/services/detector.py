"""Name and PII detection pipeline using spaCy NER and regex patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass

import spacy

# Load spaCy model once at module level
_nlp = spacy.load("en_core_web_sm")

# Regex patterns for PII types spaCy doesn't handle well
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
PHONE_PATTERN = re.compile(
    r"(?<!\d)"  # no digit before
    r"(?:"
    r"\(\d{3}\)\s*\d{3}[.\-\s]?\d{4}"  # (555) 123-4567
    r"|"
    r"\d{3}[.\-\s]\d{3}[.\-\s]\d{4}"  # 555-123-4567 / 555.123.4567
    r"|"
    r"\+?1?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"  # +1 555 123 4567
    r")"
    r"(?!\d)"  # no digit after
)


@dataclass
class DetectedEntity:
    """A detected entity in text with its location and metadata."""

    text: str
    entity_type: str  # PERSON, ORG, EMAIL, PHONE
    start: int
    end: int
    confidence: float
    source: str  # "regex", "spacy"


def _detect_regex(text: str) -> list[DetectedEntity]:
    """Detect emails and phone numbers using regex patterns."""
    entities: list[DetectedEntity] = []

    for match in EMAIL_PATTERN.finditer(text):
        entities.append(
            DetectedEntity(
                text=match.group(),
                entity_type="EMAIL",
                start=match.start(),
                end=match.end(),
                confidence=0.95,
                source="regex",
            )
        )

    for match in PHONE_PATTERN.finditer(text):
        entities.append(
            DetectedEntity(
                text=match.group(),
                entity_type="PHONE",
                start=match.start(),
                end=match.end(),
                confidence=0.90,
                source="regex",
            )
        )

    return entities


def _estimate_confidence(text: str) -> float:
    """Estimate confidence for a spaCy NER detection.

    Multi-word entities get higher confidence than single-word ones.
    """
    words = text.strip().split()
    if len(words) >= 2:
        return 0.90
    if len(words) == 1 and text[0].isupper():
        return 0.80
    return 0.60


def _detect_ner(text: str) -> list[DetectedEntity]:
    """Detect PERSON and ORG entities using spaCy NER."""
    doc = _nlp(text)
    entities: list[DetectedEntity] = []

    for ent in doc.ents:
        if ent.label_ not in ("PERSON", "ORG"):
            continue

        confidence = _estimate_confidence(ent.text)
        entities.append(
            DetectedEntity(
                text=ent.text,
                entity_type=ent.label_,
                start=ent.start_char,
                end=ent.end_char,
                confidence=confidence,
                source="spacy",
            )
        )

    return entities


def _deduplicate(entities: list[DetectedEntity]) -> list[DetectedEntity]:
    """Remove overlapping entities, preferring longer matches with higher confidence."""
    if not entities:
        return []

    # Sort by start position, then by length descending, then confidence descending
    sorted_ents = sorted(
        entities, key=lambda e: (e.start, -(e.end - e.start), -e.confidence)
    )

    result: list[DetectedEntity] = []
    for ent in sorted_ents:
        # Check if this entity overlaps with any already-accepted entity
        overlaps = False
        for accepted in result:
            if ent.start < accepted.end and ent.end > accepted.start:
                overlaps = True
                break
        if not overlaps:
            result.append(ent)

    return result


def detect_entities(
    text: str, min_confidence: float = 0.65
) -> list[DetectedEntity]:
    """Run the full detection pipeline: regex -> spaCy NER -> deduplicate -> filter.

    Args:
        text: The text to scan for entities.
        min_confidence: Minimum confidence threshold. Single-word detections
            below this threshold are filtered out.

    Returns:
        List of DetectedEntity objects sorted by start position.
    """
    # Layer 1: Regex (emails, phones)
    regex_entities = _detect_regex(text)

    # Layer 2: spaCy NER (PERSON, ORG)
    ner_entities = _detect_ner(text)

    # Combine and deduplicate
    all_entities = regex_entities + ner_entities
    deduped = _deduplicate(all_entities)

    # Filter low-confidence single-word detections
    filtered = [
        e
        for e in deduped
        if e.confidence >= min_confidence or len(e.text.split()) > 1
    ]

    # Sort by start position for consistent output
    return sorted(filtered, key=lambda e: e.start)
