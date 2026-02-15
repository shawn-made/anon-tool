"""Tests for the AnonTool web UI."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from app.web import app


@pytest.fixture
def client(tmp_path):
    """Flask test client with temp output directory."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def anon_output_dir(tmp_path):
    """Temp directory for anonymized output."""
    d = tmp_path / "output"
    d.mkdir()
    return d


class TestIndex:
    """Tests for the main page."""

    def test_get_index(self, client):
        """GET / should return 200 and HTML."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"AnonTool" in resp.data
        assert b"Anonymize" in resp.data
        assert b"De-anonymize" in resp.data

    def test_index_has_upload_form(self, client):
        """Page should contain file upload inputs."""
        resp = client.get("/")
        assert b'type="file"' in resp.data


class TestMappings:
    """Tests for the mappings endpoint."""

    def test_get_mappings_returns_json_list(self, client):
        """GET /mappings should return a JSON array."""
        resp = client.get("/mappings")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert isinstance(data, list)


class TestAnonymize:
    """Tests for the anonymize endpoint."""

    def test_no_files_returns_400(self, client):
        """POST /anonymize with no files should return 400."""
        resp = client.post("/anonymize", data={})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_unsupported_files_returns_400(self, client, anon_output_dir):
        """POST /anonymize with only unsupported file types should return 400."""
        resp = client.post("/anonymize", data={
            "files": (io.BytesIO(b"data"), "file.csv"),
            "output_dir": str(anon_output_dir),
        }, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_single_file_anonymize(self, client, anon_output_dir):
        """POST /anonymize with one .txt file should succeed."""
        content = b"John Smith met with Jane Doe at Acme Corporation."
        resp = client.post("/anonymize", data={
            "files": (io.BytesIO(content), "test.txt"),
            "output_dir": str(anon_output_dir),
        }, content_type="multipart/form-data")

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "output_path" in data
        assert "mapping_id" in data
        assert Path(data["output_path"]).exists()

        # Verify anonymization worked
        output_text = Path(data["output_path"]).read_text()
        assert "John Smith" not in output_text

    def test_multiple_files_merged(self, client, anon_output_dir):
        """POST /anonymize with multiple files and merge=true should produce one output."""
        resp = client.post("/anonymize", data={
            "files": [
                (io.BytesIO(b"John Smith is here."), "doc1.txt"),
                (io.BytesIO(b"Jane Doe is there."), "doc2.txt"),
            ],
            "output_dir": str(anon_output_dir),
            "merge": "true",
        }, content_type="multipart/form-data")

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["files_processed"] == 2
        assert Path(data["output_path"]).exists()

    def test_multiple_files_separate(self, client, anon_output_dir):
        """POST /anonymize with multiple files and merge=false should produce separate outputs."""
        resp = client.post("/anonymize", data={
            "files": [
                (io.BytesIO(b"John Smith is here."), "doc1.txt"),
                (io.BytesIO(b"Jane Doe is there."), "doc2.txt"),
            ],
            "output_dir": str(anon_output_dir),
            "merge": "false",
        }, content_type="multipart/form-data")

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["files_processed"] == 2
        assert len(data["results"]) == 2

    def test_custom_mapping_id(self, client, anon_output_dir):
        """Should use provided mapping ID."""
        content = b"Sarah Johnson works at TechStart."
        resp = client.post("/anonymize", data={
            "files": (io.BytesIO(content), "test.txt"),
            "output_dir": str(anon_output_dir),
            "mapping_id": "my_custom_id",
        }, content_type="multipart/form-data")

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["mapping_id"] == "my_custom_id"


class TestDeanonymize:
    """Tests for the de-anonymize endpoint."""

    def test_no_file_returns_400(self, client):
        """POST /deanonymize with no file should return 400."""
        resp = client.post("/deanonymize", data={"mapping_id": "test"})
        assert resp.status_code == 400

    def test_no_mapping_id_returns_400(self, client):
        """POST /deanonymize without mapping_id should return 400."""
        resp = client.post("/deanonymize", data={
            "file": (io.BytesIO(b"Person_A is here."), "test.anon.txt"),
        }, content_type="multipart/form-data")
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "Mapping ID" in data["error"]

    def test_round_trip(self, client, anon_output_dir):
        """Anonymize then de-anonymize should produce original content."""
        original = b"Robert Garcia met with Lisa Wang at Global Finance Corp."

        # Step 1: Anonymize
        resp = client.post("/anonymize", data={
            "files": (io.BytesIO(original), "roundtrip.txt"),
            "output_dir": str(anon_output_dir),
            "mapping_id": "rt_test",
        }, content_type="multipart/form-data")
        assert resp.status_code == 200
        anon_data = json.loads(resp.data)

        # Step 2: Read anonymized file and de-anonymize
        anon_path = Path(anon_data["output_path"])
        anon_content = anon_path.read_bytes()

        resp = client.post("/deanonymize", data={
            "file": (io.BytesIO(anon_content), "roundtrip.anon.txt"),
            "output_dir": str(anon_output_dir),
            "mapping_id": "rt_test",
        }, content_type="multipart/form-data")
        assert resp.status_code == 200
        deanon_data = json.loads(resp.data)

        restored = Path(deanon_data["output_path"]).read_text()
        assert restored == original.decode()
