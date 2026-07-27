"""Flask web app: NCT number in, patient-friendly bullet-point summary out."""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from clinical_trials import (
    TrialFetchError,
    fetch_study,
    normalize_nct_id,
    summarize_study,
)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/summary")
def api_summary():
    """Return a JSON summary for the given ?nct=NCTXXXXXXXX query parameter."""
    nct_param = request.args.get("nct", "")
    try:
        canonical = normalize_nct_id(nct_param)
        raw = fetch_study(canonical)
        summary = summarize_study(raw)
    except TrialFetchError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(summary)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
