"""
BetPawa Virtual Football — Signal & Pattern Detector
Flask API Server
"""

import os
import json
import time
import threading
import logging
from flask import Flask, jsonify, send_file, render_template, send_from_directory
from flask_cors import CORS
from scraper import BetPawaScraper
from pattern_engine import PatternEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

DATA_FILE = "data/matches.json"
PATTERNS_FILE = "data/patterns.json"

scraper = BetPawaScraper()
engine = PatternEngine()

# Background polling state
poll_state = {"running": False, "last_run": None, "status": "idle", "matches_collected": 0}


def background_poll():
    """Continuous background data collection loop."""
    logger.info("Background polling started.")
    while poll_state["running"]:
        try:
            poll_state["status"] = "fetching"
            matches = scraper.fetch_all_leagues()
            if matches:
                existing = load_json(DATA_FILE, [])
                # Deduplicate by match_id
                ids = {m["match_id"] for m in existing}
                new_matches = [m for m in matches if m["match_id"] not in ids]
                existing.extend(new_matches)
                save_json(DATA_FILE, existing)
                poll_state["matches_collected"] = len(existing)
                logger.info(f"Added {len(new_matches)} new matches. Total: {len(existing)}")

                # Re-run pattern detection
                poll_state["status"] = "analyzing"
                patterns = engine.detect_patterns(existing)
                save_json(PATTERNS_FILE, patterns)
                logger.info(f"Patterns detected: {len(patterns)}")

            poll_state["status"] = "sleeping"
            poll_state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(f"Poll error: {e}")
            poll_state["status"] = "error"

        # Wait 90-180s between polls (human-like interval)
        import random
        wait = random.randint(90, 180)
        logger.info(f"Sleeping {wait}s until next poll...")
        for _ in range(wait):
            if not poll_state["running"]:
                break
            time.sleep(1)

    poll_state["status"] = "stopped"
    logger.info("Background polling stopped.")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    return jsonify({
        "poll_running": poll_state["running"],
        "status": poll_state["status"],
        "last_run": poll_state["last_run"],
        "matches_collected": poll_state["matches_collected"],
    })


@app.route("/api/start", methods=["POST"])
def start_polling():
    if poll_state["running"]:
        return jsonify({"message": "Already running"}), 200
    poll_state["running"] = True
    t = threading.Thread(target=background_poll, daemon=True)
    t.start()
    return jsonify({"message": "Polling started"})


@app.route("/api/stop", methods=["POST"])
def stop_polling():
    poll_state["running"] = False
    return jsonify({"message": "Polling stopping..."})


@app.route("/api/matches")
def get_matches():
    matches = load_json(DATA_FILE, [])
    return jsonify({"total": len(matches), "matches": matches[-200:]})  # last 200


@app.route("/api/patterns")
def get_patterns():
    patterns = load_json(PATTERNS_FILE, [])
    return jsonify({"total": len(patterns), "patterns": patterns})


@app.route("/api/stats")
def get_stats():
    matches = load_json(DATA_FILE, [])
    patterns = load_json(PATTERNS_FILE, [])
    over35 = [m for m in matches if m.get("total_goals", 0) > 3.5]
    leagues = {}
    for m in matches:
        lg = m.get("league", "Unknown")
        leagues[lg] = leagues.get(lg, 0) + 1
    return jsonify({
        "total_matches": len(matches),
        "over35_count": len(over35),
        "over35_rate": round(len(over35) / len(matches) * 100, 1) if matches else 0,
        "total_patterns": len(patterns),
        "leagues": leagues,
    })


@app.route("/api/download/patterns")
def download_patterns():
    if not os.path.exists(PATTERNS_FILE):
        return jsonify({"error": "No patterns file yet"}), 404
    return send_file(
        PATTERNS_FILE,
        as_attachment=True,
        download_name="betpawa_patterns.json",
        mimetype="application/json",
    )


@app.route("/api/download/matches")
def download_matches():
    if not os.path.exists(DATA_FILE):
        return jsonify({"error": "No matches file yet"}), 404
    return send_file(
        DATA_FILE,
        as_attachment=True,
        download_name="betpawa_matches.json",
        mimetype="application/json",
    )


@app.route("/api/download/report")
def download_report():
    """Generate and download a human-readable CSV report."""
    import csv
    import io
    patterns = load_json(PATTERNS_FILE, [])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Pattern Type", "League", "Description", "Occurrences",
                     "Over 3.5 Hit Rate %", "Avg Goals", "Signal Strength", "Details"])
    for p in patterns:
        writer.writerow([
            p.get("type", ""),
            p.get("league", ""),
            p.get("description", ""),
            p.get("occurrences", ""),
            p.get("over35_rate", ""),
            p.get("avg_goals", ""),
            p.get("signal_strength", ""),
            p.get("details", ""),
        ])
    output.seek(0)
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=betpawa_patterns_report.csv"},
    )


@app.route("/api/scan_now", methods=["POST"])
def scan_now():
    """Trigger an immediate single scan."""
    try:
        matches = scraper.fetch_all_leagues()
        existing = load_json(DATA_FILE, [])
        ids = {m["match_id"] for m in existing}
        new_matches = [m for m in matches if m["match_id"] not in ids]
        existing.extend(new_matches)
        save_json(DATA_FILE, existing)
        patterns = engine.detect_patterns(existing)
        save_json(PATTERNS_FILE, patterns)
        poll_state["matches_collected"] = len(existing)
        poll_state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        return jsonify({
            "new_matches": len(new_matches),
            "total_matches": len(existing),
            "patterns_found": len(patterns),
        })
    except Exception as e:
        logger.error(f"Scan error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    app.run(debug=False, host="0.0.0.0", port=5000)
