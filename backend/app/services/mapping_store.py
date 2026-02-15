"""JSON key file read/write/lookup for pseudonym mappings."""

from __future__ import annotations

import json
import string
from datetime import datetime, timezone
from pathlib import Path


def _default_base_dir() -> Path:
    """Return the default AnonTool data directory (~/.anontool)."""
    return Path.home() / ".anontool"


def _next_letter_label(index: int) -> str:
    """Convert a 0-based index to a letter label: 0->A, 25->Z, 26->AA, etc."""
    letters = string.ascii_uppercase
    if index < 26:
        return letters[index]
    # For index >= 26, produce AA, AB, ... AZ, BA, ...
    result = ""
    i = index
    while True:
        result = letters[i % 26] + result
        i = i // 26 - 1
        if i < 0:
            break
    return result


class MappingStore:
    """Manages pseudonym mappings stored as JSON key files.

    Each mapping has a unique ID and stores the bidirectional relationship
    between real names and their pseudonyms.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialize the mapping store.

        Args:
            base_dir: Root directory for AnonTool data. Defaults to ~/.anontool.
        """
        self._base_dir = base_dir or _default_base_dir()
        self._mappings_dir = self._base_dir / "mappings"
        self._mappings_dir.mkdir(parents=True, exist_ok=True)

        self._mapping_id: str | None = None
        self._data: dict = {}

    @property
    def mapping_id(self) -> str | None:
        """Return the current mapping ID."""
        return self._mapping_id

    def create_or_load(self, mapping_id: str) -> dict:
        """Load an existing mapping or create a new empty one.

        Args:
            mapping_id: Unique identifier for this mapping.

        Returns:
            The mapping data dict.
        """
        self._mapping_id = mapping_id
        path = self._mappings_dir / f"{mapping_id}.json"

        if path.exists():
            with open(path) as f:
                self._data = json.load(f)
        else:
            now = datetime.now(timezone.utc).isoformat()
            self._data = {
                "mapping_id": mapping_id,
                "created": now,
                "updated": now,
                "entries": {},
            }

        return self._data

    def get_pseudonym(self, real_name: str, entity_type: str) -> str:
        """Get or create a pseudonym for a real name.

        If the name already has a pseudonym in this mapping, return it.
        Otherwise, generate the next sequential pseudonym.

        Args:
            real_name: The original name/value to pseudonymize.
            entity_type: The entity type (PERSON, ORG, EMAIL, PHONE).

        Returns:
            The pseudonym string (e.g., "Person_A", "Company_1").
        """
        entries = self._data.get("entries", {})

        # Check if already mapped
        if real_name in entries:
            return entries[real_name]["pseudonym"]

        # Count existing entries of this type to determine next index
        existing_count = sum(
            1 for e in entries.values() if e["type"] == entity_type
        )

        pseudonym = self._generate_pseudonym(entity_type, existing_count)

        entries[real_name] = {
            "pseudonym": pseudonym,
            "type": entity_type,
        }
        self._data["entries"] = entries
        self._data["updated"] = datetime.now(timezone.utc).isoformat()

        return pseudonym

    def _generate_pseudonym(self, entity_type: str, index: int) -> str:
        """Generate a pseudonym based on entity type and sequence index.

        Args:
            entity_type: PERSON, ORG, EMAIL, or PHONE.
            index: 0-based count of existing entries of this type.

        Returns:
            Pseudonym string like Person_A, Company_1, Email_1, Phone_1.
        """
        if entity_type == "PERSON":
            return f"Person_{_next_letter_label(index)}"
        if entity_type == "ORG":
            return f"Company_{index + 1}"
        if entity_type == "EMAIL":
            return f"Email_{index + 1}"
        if entity_type == "PHONE":
            return f"Phone_{index + 1}"
        return f"Entity_{index + 1}"

    def save(self) -> Path:
        """Write the current mapping to its JSON file.

        Returns:
            Path to the saved JSON file.
        """
        if not self._mapping_id:
            raise ValueError("No mapping loaded. Call create_or_load() first.")

        self._data["updated"] = datetime.now(timezone.utc).isoformat()
        path = self._mappings_dir / f"{self._mapping_id}.json"

        with open(path, "w") as f:
            json.dump(self._data, f, indent=2)

        return path

    def get_entries(self) -> dict:
        """Return the current mapping entries."""
        return self._data.get("entries", {})

    def get_reverse_lookup(self) -> dict[str, str]:
        """Build a reverse lookup: pseudonym -> real_name."""
        entries = self._data.get("entries", {})
        return {v["pseudonym"]: k for k, v in entries.items()}

    def list_mappings(self) -> list[str]:
        """Return all available mapping IDs from the mappings directory."""
        return sorted(
            p.stem for p in self._mappings_dir.glob("*.json")
        )
