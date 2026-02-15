"""Web UI for AnonTool — local Flask server."""

from __future__ import annotations

import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, render_template

from app.services.anonymizer import anonymize_file, anonymize_folder, deanonymize_file
from app.services.mapping_store import MappingStore

app = Flask(__name__)

_SUPPORTED_EXTENSIONS = {".txt", ".md"}


@app.errorhandler(Exception)
def handle_error(e):
    """Return JSON error responses instead of HTML for all errors."""
    return jsonify({"error": str(e)}), 500


def _resolve_output_dir(output_dir: str | None) -> Path:
    """Resolve the output directory, defaulting to ~/Downloads."""
    if output_dir and output_dir.strip():
        path = Path(output_dir).expanduser()
    else:
        path = Path.home() / "Downloads"
    path.mkdir(parents=True, exist_ok=True)
    return path


@app.route("/")
def index():
    """Serve the main UI page."""
    return render_template("index.html")


@app.route("/mappings")
def list_mappings():
    """Return available mapping IDs as JSON."""
    store = MappingStore()
    return jsonify(store.list_mappings())


@app.route("/anonymize", methods=["POST"])
def anonymize():
    """Anonymize uploaded file(s)."""
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files uploaded"}), 400

    output_dir = _resolve_output_dir(request.form.get("output_dir"))
    mapping_id = request.form.get("mapping_id") or None
    merge = request.form.get("merge") == "true"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        saved_files = []

        for f in files:
            if not f.filename:
                continue
            ext = Path(f.filename).suffix.lower()
            if ext not in _SUPPORTED_EXTENSIONS:
                continue
            dest = tmp / f.filename
            f.save(dest)
            saved_files.append(dest)

        if not saved_files:
            return jsonify({
                "error": "No supported files (.txt, .md) found in upload"
            }), 400

        if len(saved_files) > 1 and merge:
            # Bulk mode — merge into single output
            output_path = output_dir / "anonymized_merged.txt"
            result = anonymize_folder(
                folder_path=tmp,
                output_path=output_path,
                mapping_id=mapping_id,
            )
            return jsonify({
                "output_path": result.output_path,
                "mapping_id": result.mapping_id,
                "entities_found": result.total_entities,
                "files_processed": result.files_processed,
                "files_failed": result.files_failed,
                "failed_files": [
                    {"name": n, "error": e} for n, e in result.failed_files
                ],
            })
        elif len(saved_files) > 1:
            # Multiple files, individual outputs
            results = []
            for sf in saved_files:
                out = output_dir / f"{sf.stem}.anon{sf.suffix}"
                r = anonymize_file(
                    input_path=sf,
                    output_path=out,
                    mapping_id=mapping_id,
                )
                # Reuse the mapping_id from the first file for consistency
                if mapping_id is None:
                    mapping_id = r["mapping_id"]
                results.append(r)
            return jsonify({
                "files_processed": len(results),
                "results": results,
            })
        else:
            # Single file
            sf = saved_files[0]
            out = output_dir / f"{sf.stem}.anon{sf.suffix}"
            result = anonymize_file(
                input_path=sf,
                output_path=out,
                mapping_id=mapping_id,
            )
            return jsonify(result)


@app.route("/deanonymize", methods=["POST"])
def deanonymize():
    """De-anonymize an uploaded file."""
    f = request.files.get("file")
    if not f or f.filename == "":
        return jsonify({"error": "No file uploaded"}), 400

    mapping_id = request.form.get("mapping_id")
    if not mapping_id:
        return jsonify({"error": "Mapping ID is required"}), 400

    output_dir = _resolve_output_dir(request.form.get("output_dir"))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        dest = tmp / f.filename
        f.save(dest)

        stem = dest.stem
        if stem.endswith(".anon"):
            stem = stem[: -len(".anon")]
        out = output_dir / f"{stem}.restored{dest.suffix}"

        result = deanonymize_file(
            input_path=dest,
            mapping_id=mapping_id,
            output_path=out,
        )
        return jsonify(result)


def main() -> None:
    """Run the web server."""
    print("Starting AnonTool Web UI at http://localhost:8080")
    app.run(debug=True, port=8080)


if __name__ == "__main__":
    main()
