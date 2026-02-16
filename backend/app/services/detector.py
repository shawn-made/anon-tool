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


_MAX_CHUNK_SIZE = 900_000  # Stay under spaCy's 1M limit with margin


def _split_into_chunks(text: str) -> list[tuple[str, int]]:
    """Split text into chunks at line boundaries, each under spaCy's limit.

    Args:
        text: The full text to split.

    Returns:
        List of (chunk_text, offset) tuples where offset is the
        character position of the chunk start in the original text.
    """
    if len(text) <= _MAX_CHUNK_SIZE:
        return [(text, 0)]

    chunks: list[tuple[str, int]] = []
    start = 0
    while start < len(text):
        end = start + _MAX_CHUNK_SIZE
        if end >= len(text):
            chunks.append((text[start:], start))
            break
        # Find the last newline before the limit to split cleanly
        split_at = text.rfind("\n", start, end)
        if split_at <= start:
            # No newline found — split at the limit
            split_at = end
        else:
            split_at += 1  # Include the newline in this chunk
        chunks.append((text[start:split_at], start))
        start = split_at

    return chunks


def _detect_ner(text: str) -> list[DetectedEntity]:
    """Detect PERSON and ORG entities using spaCy NER.

    Automatically chunks large texts to stay within spaCy's character limit.
    """
    chunks = _split_into_chunks(text)
    entities: list[DetectedEntity] = []

    for chunk_text, offset in chunks:
        doc = _nlp(chunk_text)
        for ent in doc.ents:
            if ent.label_ not in ("PERSON", "ORG"):
                continue

            confidence = _estimate_confidence(ent.text)
            entities.append(
                DetectedEntity(
                    text=ent.text,
                    entity_type=ent.label_,
                    start=ent.start_char + offset,
                    end=ent.end_char + offset,
                    confidence=confidence,
                    source="spacy",
                )
            )

    return entities


def _is_inside_email(ent: DetectedEntity, text: str) -> bool:
    """Check if an ORG/PERSON entity is embedded inside an email address.

    Catches cases where spaCy detects the domain (e.g., 'Harvard') as an ORG
    but the surrounding text is an email like jsmith@harvard.edu.
    """
    if ent.entity_type in ("EMAIL", "PHONE"):
        return False

    # Look for @ before the entity and . + TLD after it
    search_start = max(0, ent.start - 50)
    before = text[search_start : ent.start]
    after = text[ent.end : ent.end + 10]

    has_at_before = "@" in before and " " not in before[before.rfind("@") :]
    has_tld_after = re.match(r"\.[A-Za-z]{2,}\b", after) is not None

    return has_at_before and has_tld_after


def _deduplicate(
    entities: list[DetectedEntity], text: str = ""
) -> list[DetectedEntity]:
    """Remove overlapping entities, preferring longer matches with higher confidence."""
    if not entities:
        return []

    # Sort by start position, then by length descending, then confidence descending
    sorted_ents = sorted(
        entities, key=lambda e: (e.start, -(e.end - e.start), -e.confidence)
    )

    result: list[DetectedEntity] = []
    for ent in sorted_ents:
        # Drop ORG/PERSON entities that are inside an email address
        if text and _is_inside_email(ent, text):
            continue

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
    deduped = _deduplicate(all_entities, text)

    # Filter low-confidence single-word detections
    filtered = [
        e
        for e in deduped
        if e.confidence >= min_confidence or len(e.text.split()) > 1
    ]

    # Sort by start position for consistent output
    return sorted(filtered, key=lambda e: e.start)
