"""Flask web app: summarize a trial by NCT number, or search for trials."""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from clinical_trials import (
    TrialFetchError,
    fetch_study,
    normalize_nct_id,
    search_studies,
    summarize_study,
)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search_page():
    return render_template("search.html")


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


@app.route("/api/search")
def api_search():
    """Search trials by ?condition=, optional ?location= and ?max_time= level."""
    condition = request.args.get("condition", "")
    location = request.args.get("location", "")
    max_time = request.args.get("max_time", "")
    try:
        results = search_studies(
            condition=condition,
            location=location or None,
            max_level=max_time or None,
        )
    except TrialFetchError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(results)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
