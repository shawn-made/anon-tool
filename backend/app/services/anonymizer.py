"""Core anonymize/de-anonymize logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.services.detector import DetectedEntity, detect_entities
from app.services.mapping_store import MappingStore

_SUPPORTED_EXTENSIONS = {".txt", ".md"}


@dataclass
class AnonymizeResult:
    """Result of an anonymization operation."""

    anonymized_text: str
    entities_found: list[DetectedEntity] = field(default_factory=list)
    mapping_id: str = ""


def anonymize_text(
    text: str,
    mapping_id: str,
    base_dir: Path | None = None,
    use_ollama: bool = False,
) -> AnonymizeResult:
    """Anonymize text by detecting entities and replacing with pseudonyms.

    Args:
        text: The input text to anonymize.
        mapping_id: ID for the pseudonym mapping (creates or reuses).
        base_dir: Override base directory for mapping storage.
        use_ollama: Whether to use Ollama for entity verification.

    Returns:
        AnonymizeResult with anonymized text, detected entities, and mapping ID.
    """
    # Step 1: Detect entities
    entities = detect_entities(text)

    # Step 1b: Optionally verify with Ollama
    if use_ollama:
        try:
            from app.services.ollama_client import OllamaClient

            client = OllamaClient()
            if client.is_available():
                entities = client.verify_entities(text, entities)
        except Exception:
            pass  # Graceful fallback — use spaCy-only results

    # Step 2: Get pseudonyms from mapping store
    store = MappingStore(base_dir=base_dir)
    store.create_or_load(mapping_id)

    # Step 3: Replace entities right-to-left to preserve character offsets
    result_text = text
    # Sort entities by start position descending (right-to-left replacement)
    sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)

    for entity in sorted_entities:
        pseudonym = store.get_pseudonym(entity.text, entity.entity_type)
        result_text = (
            result_text[: entity.start] + pseudonym + result_text[entity.end :]
        )

    # Step 3b: Second pass — replace any remaining occurrences of mapped names
    # that spaCy missed (e.g., names in list/heading contexts).
    # Sort by length descending so longer names are replaced first.
    entries = store.get_entries()
    sorted_names = sorted(entries.keys(), key=len, reverse=True)
    for real_name in sorted_names:
        pseudonym = entries[real_name]["pseudonym"]
        result_text = result_text.replace(real_name, pseudonym)

    # Step 4: Save the mapping
    store.save()

    return AnonymizeResult(
        anonymized_text=result_text,
        entities_found=entities,
        mapping_id=mapping_id,
    )


def deanonymize_text(
    text: str,
    mapping_id: str,
    base_dir: Path | None = None,
) -> str:
    """Restore anonymized text by replacing pseudonyms with original names.

    Args:
        text: The anonymized text to restore.
        mapping_id: ID of the mapping to use for restoration.
        base_dir: Override base directory for mapping storage.

    Returns:
        The de-anonymized text with original names restored.

    Raises:
        FileNotFoundError: If the mapping file doesn't exist.
    """
    store = MappingStore(base_dir=base_dir)
    data = store.create_or_load(mapping_id)

    if not data.get("entries"):
        return text

    reverse = store.get_reverse_lookup()

    # Sort pseudonyms by length descending to handle substring cases
    # (e.g., "Person_AA" before "Person_A")
    sorted_pseudonyms = sorted(reverse.keys(), key=len, reverse=True)

    result = text
    for pseudonym in sorted_pseudonyms:
        real_name = reverse[pseudonym]
        result = result.replace(pseudonym, real_name)

    return result


def _default_output_dir() -> Path:
    """Return the default output directory."""
    output_dir = Path.home() / ".anontool" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _generate_mapping_id(input_path: Path) -> str:
    """Generate a mapping ID based on filename and timestamp."""
    stem = input_path.stem
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{stem}_{ts}"


def anonymize_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    mapping_id: str | None = None,
    base_dir: Path | None = None,
    use_ollama: bool = False,
) -> dict:
    """Anonymize a file and write the result.

    Args:
        input_path: Path to the input file.
        output_path: Path for the output file. Auto-generated if None.
        mapping_id: Mapping ID to use. Auto-generated if None.
        base_dir: Override base directory for mapping storage.
        use_ollama: Whether to use Ollama for entity verification.

    Returns:
        Dict with keys: output_path, mapping_id, entities_found.
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if input_path.suffix not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {input_path.suffix}. "
            f"Supported: {', '.join(_SUPPORTED_EXTENSIONS)}"
        )

    # Read input
    text = input_path.read_text(encoding="utf-8")

    # Generate defaults
    if mapping_id is None:
        mapping_id = _generate_mapping_id(input_path)

    if output_path is None:
        out_dir = _default_output_dir()
        output_path = out_dir / f"{input_path.stem}.anon{input_path.suffix}"
    else:
        output_path = Path(output_path)

    # Anonymize
    result = anonymize_text(
        text, mapping_id, base_dir=base_dir, use_ollama=use_ollama
    )

    # Write output (never modify input)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.anonymized_text, encoding="utf-8")

    return {
        "output_path": str(output_path),
        "mapping_id": result.mapping_id,
        "entities_found": len(result.entities_found),
    }


def deanonymize_file(
    input_path: str | Path,
    mapping_id: str,
    output_path: str | Path | None = None,
    base_dir: Path | None = None,
) -> dict:
    """De-anonymize a file using a mapping and write the result.

    Args:
        input_path: Path to the anonymized file.
        mapping_id: Mapping ID to use for restoration.
        output_path: Path for the output file. Auto-generated if None.
        base_dir: Override base directory for mapping storage.

    Returns:
        Dict with keys: output_path, mapping_id.
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Read input
    text = input_path.read_text(encoding="utf-8")

    # Generate output path
    if output_path is None:
        out_dir = _default_output_dir()
        # Remove .anon suffix if present, add .restored
        stem = input_path.stem
        if stem.endswith(".anon"):
            stem = stem[: -len(".anon")]
        output_path = out_dir / f"{stem}.restored{input_path.suffix}"
    else:
        output_path = Path(output_path)

    # De-anonymize
    restored = deanonymize_text(text, mapping_id, base_dir=base_dir)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(restored, encoding="utf-8")

    return {
        "output_path": str(output_path),
        "mapping_id": mapping_id,
    }
