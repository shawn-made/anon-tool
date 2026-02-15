"""Tests for the JSON mapping store."""

import json

import pytest

from app.services.mapping_store import MappingStore, _next_letter_label


class TestNextLetterLabel:
    """Tests for the letter-label generator."""

    def test_first_letter(self):
        assert _next_letter_label(0) == "A"

    def test_last_single_letter(self):
        assert _next_letter_label(25) == "Z"

    def test_double_letter_aa(self):
        assert _next_letter_label(26) == "AA"

    def test_double_letter_ab(self):
        assert _next_letter_label(27) == "AB"

    def test_double_letter_az(self):
        assert _next_letter_label(51) == "AZ"


class TestMappingStoreCreateLoad:
    """Tests for creating and loading mappings."""

    def test_create_new_mapping(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        data = store.create_or_load("test-mapping")
        assert data["mapping_id"] == "test-mapping"
        assert "created" in data
        assert "entries" in data
        assert data["entries"] == {}

    def test_load_existing_mapping(self, tmp_anontool_dir):
        # Create and save a mapping first
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("persist-test")
        store.get_pseudonym("John Smith", "PERSON")
        store.save()

        # Load it in a new store instance
        store2 = MappingStore(base_dir=tmp_anontool_dir)
        data = store2.create_or_load("persist-test")
        assert "John Smith" in data["entries"]
        assert data["entries"]["John Smith"]["pseudonym"] == "Person_A"

    def test_mapping_id_property(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        assert store.mapping_id is None
        store.create_or_load("my-id")
        assert store.mapping_id == "my-id"


class TestGetPseudonym:
    """Tests for pseudonym generation and lookup."""

    def test_person_first(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("test")
        assert store.get_pseudonym("John Smith", "PERSON") == "Person_A"

    def test_person_second(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("test")
        store.get_pseudonym("John Smith", "PERSON")
        assert store.get_pseudonym("Jane Doe", "PERSON") == "Person_B"

    def test_same_name_returns_same_pseudonym(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("test")
        p1 = store.get_pseudonym("John Smith", "PERSON")
        p2 = store.get_pseudonym("John Smith", "PERSON")
        assert p1 == p2 == "Person_A"

    def test_org_pseudonym(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("test")
        assert store.get_pseudonym("Acme Corp", "ORG") == "Company_1"
        assert store.get_pseudonym("Globex Inc", "ORG") == "Company_2"

    def test_email_pseudonym(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("test")
        assert store.get_pseudonym("john@example.com", "EMAIL") == "Email_1"

    def test_phone_pseudonym(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("test")
        assert store.get_pseudonym("(555) 123-4567", "PHONE") == "Phone_1"

    def test_mixed_types_independent_counters(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("test")
        store.get_pseudonym("John Smith", "PERSON")
        store.get_pseudonym("Acme Corp", "ORG")
        # Second person should be B, not affected by the ORG entry
        assert store.get_pseudonym("Jane Doe", "PERSON") == "Person_B"
        # Second org should be 2
        assert store.get_pseudonym("Globex Inc", "ORG") == "Company_2"


class TestSaveAndPersist:
    """Tests for saving mappings to disk."""

    def test_save_creates_json_file(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("save-test")
        store.get_pseudonym("Alice", "PERSON")
        path = store.save()
        assert path.exists()
        assert path.name == "save-test.json"

    def test_save_without_load_raises(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        with pytest.raises(ValueError):
            store.save()

    def test_saved_json_structure(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("struct-test")
        store.get_pseudonym("Bob Thompson", "PERSON")
        path = store.save()

        with open(path) as f:
            data = json.load(f)

        assert data["mapping_id"] == "struct-test"
        assert "created" in data
        assert "updated" in data
        assert "Bob Thompson" in data["entries"]
        assert data["entries"]["Bob Thompson"]["pseudonym"] == "Person_A"
        assert data["entries"]["Bob Thompson"]["type"] == "PERSON"


class TestReverseLookup:
    """Tests for reverse lookup (pseudonym -> real name)."""

    def test_reverse_lookup(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("rev-test")
        store.get_pseudonym("John Smith", "PERSON")
        store.get_pseudonym("Acme Corp", "ORG")
        reverse = store.get_reverse_lookup()
        assert reverse["Person_A"] == "John Smith"
        assert reverse["Company_1"] == "Acme Corp"


class TestListMappings:
    """Tests for listing available mappings."""

    def test_list_empty(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        assert store.list_mappings() == []

    def test_list_after_save(self, tmp_anontool_dir):
        store = MappingStore(base_dir=tmp_anontool_dir)
        store.create_or_load("mapping-alpha")
        store.save()
        store.create_or_load("mapping-beta")
        store.save()
        ids = store.list_mappings()
        assert "mapping-alpha" in ids
        assert "mapping-beta" in ids
        assert len(ids) == 2
