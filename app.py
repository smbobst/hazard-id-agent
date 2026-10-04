"""Hazard Identification Agent — web app entry point.

Local:   python app.py            (then open http://localhost:8000)
Hosted:  gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300
"""
import hmac
import json
import os
from datetime import date
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
import io

BASE = Path(__file__).parent


def _load_dotenv():
    """Read KEY=value lines from a local .env file (for running on your own computer)."""
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

from hazid.ctx_client import CTXClient, CTXError, valid_cas  # noqa: E402
from hazid.processing import build_bundles  # noqa: E402
from hazid.prompts import SYSTEM_PROMPT, user_message  # noqa: E402
from hazid.llm import write_summary, LLMError  # noqa: E402
from hazid.export_docx import markdown_to_docx  # noqa: E402

app = Flask(__name__, static_folder="static")
MOCK = os.getenv("MOCK_MODE", "").lower() in ("1", "true", "yes")


def _authorized() -> bool:
    pw = os.getenv("APP_PASSWORD", "")
    if not pw:
        return True
    given = request.headers.get("X-App-Password", "")
    return hmac.compare_digest(given.encode(), pw.encode())


def _compact(obj):
    """Drop empty fields so the evidence package sent to Claude stays small."""
    if isinstance(obj, dict):
        return {k: _compact(v) for k, v in obj.items() if v not in (None, "", "-", [], {})}
    if isinstance(obj, list):
        return [_compact(v) for v in obj]
    return obj


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/config")
def config():
    return jsonify({
        "password_required": bool(os.getenv("APP_PASSWORD")),
        "mock_mode": MOCK,
        "ctx_key_set": bool(os.getenv("CTX_API_KEY")),
        "anthropic_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
    })


@app.get("/healthz")
def health():
    return "ok"


@app.post("/api/summary")
def summary():
    if not _authorized():
        return jsonify({"error": "Incorrect access password."}), 401
    cas = (request.get_json(silent=True) or {}).get("cas", "").strip()
    if not valid_cas(cas):
        return jsonify({"error": f"'{cas}' is not a valid CAS Registry Number (check the format and check digit)."}), 400

    retrieved_on = date.today().isoformat()
    try:
        if MOCK:
            sample = json.loads((BASE / "sample_data" / "mock_raw.json").read_text())
            chem, raw = sample["chemical"], sample["raw"]
        else:
            client = CTXClient(os.getenv("CTX_API_KEY", ""))
            chem = client.resolve_cas(cas)
            raw = client.fetch_hazard(chem["dtxsid"])
    except CTXError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Problem contacting the EPA CTX API: {e}"}), 502

    bundle = build_bundles(chem, raw)
    llm_input = {k: v for k, v in bundle.items() if k != "sources"}
    bundle_json = json.dumps(_compact(llm_input), separators=(",", ":"), default=str)

    try:
        if MOCK and not os.getenv("ANTHROPIC_API_KEY"):
            result = {
                "markdown": (BASE / "sample_data" / "mock_summary.md").read_text(),
                "model": "mock (no Anthropic call)", "usage": {}, "truncated": False,
            }
        else:
            result = write_summary(SYSTEM_PROMPT, user_message(bundle_json, retrieved_on))
    except LLMError as e:
        return jsonify({"error": str(e), "chemical": chem, "sources": bundle["sources"], "coverage": bundle["coverage"]}), 502

    return jsonify({
        "chemical": chem,
        "retrieved_on": retrieved_on,
        "summary_markdown": result["markdown"],
        "model": result["model"],
        "usage": result["usage"],
        "truncated": result["truncated"],
        "coverage": bundle["coverage"],
        "sources": bundle["sources"],
        "evidence_package": llm_input,
    })


@app.post("/api/export/docx")
def export_docx():
    if not _authorized():
        return jsonify({"error": "Incorrect access password."}), 401
    data = request.get_json(silent=True) or {}
    md = data.get("markdown", "")
    name = "".join(c for c in data.get("filename", "hazard_id_summary") if c.isalnum() or c in "-_") or "hazard_id_summary"
    return send_file(
        io.BytesIO(markdown_to_docx(md)),
        as_attachment=True,
        download_name=f"{name}.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"\n  Hazard ID Agent running — open http://localhost:{port} in your browser.\n  Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1", port=port, debug=False)
