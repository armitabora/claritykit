
from __future__ import annotations

import csv
import io
from flask import Flask, jsonify, render_template, request, Response

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  

from analyzer import analyze_notice


def safe_csv_cell(value):
    """Reduce spreadsheet-formula injection risk in exported user-supplied text."""
    cell = "" if value is None else str(value)
    if cell.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + cell
    return cell


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/analyze")
def api_analyze():
    payload = request.get_json(silent=True) or request.form
    text = payload.get("notice", "") if hasattr(payload, "get") else ""
    try:
        results = analyze_notice(text)
        return jsonify({"ok": True, "results": results})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/export.csv")
def export_csv():
    payload = request.get_json(silent=True) or {}
    findings = payload.get("findings", [])
    dates = payload.get("dates", [])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "finding", "explanation_or_context", "timing"])
    for finding in findings:
        writer.writerow([safe_csv_cell(finding.get("category", "")), safe_csv_cell(finding.get("evidence", "")), safe_csv_cell(finding.get("note", "")), ""])
    for item in dates:
        writer.writerow(["Date spotted", safe_csv_cell(item.get("raw", "")), safe_csv_cell(item.get("context", "")), safe_csv_cell(item.get("timing", ""))])
    response = Response("\ufeff" + output.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = 'attachment; filename="claritykit-findings.csv"'
    return response


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"ok": False, "error": "That notice is too large. Please paste a shorter section (maximum 50,000 characters)."}), 413


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
