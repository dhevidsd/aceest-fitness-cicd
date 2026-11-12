"""ACEest Fitness & Gym - v1.0.0: health, programs and calorie estimation."""
import os
import socket

from flask import Flask, jsonify, request

APP_NAME = "ACEest Fitness & Gym"
VERSION = "1.0.0"

PROGRAMS = {
    "Fat Loss (FL)": {"factor": 22},
    "Muscle Gain (MG)": {"factor": 35},
    "Beginner (BG)": {"factor": 26},
}


def estimate_calories(weight, program):
    if program not in PROGRAMS:
        raise ValueError(f"Unknown program: {program}")
    if not isinstance(weight, (int, float)) or weight <= 0:
        raise ValueError("weight must be positive")
    return round(weight * PROGRAMS[program]["factor"])


def create_app():
    # Stateless JSON API (no cookies/sessions), so CSRF protection does not apply.
    app = Flask(__name__)  # NOSONAR

    @app.after_request
    def add_version_header(response):
        response.headers["X-App-Version"] = VERSION
        return response

    @app.route("/")
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/version")
    def version():
        return jsonify({
            "app": APP_NAME,
            "version": VERSION,
            "track": os.environ.get("DEPLOYMENT_TRACK", "stable"),
            "hostname": socket.gethostname(),
        }), 200

    @app.route("/programs", methods=["GET"])
    def programs():
        return jsonify(
            [{"name": n, "factor": d["factor"]} for n, d in PROGRAMS.items()]
        ), 200

    @app.route("/calories", methods=["POST"])
    def calories():
        data = request.get_json(silent=True) or {}
        program = data.get("program")
        try:
            value = estimate_calories(data.get("weight"), program)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"calories": value, "program": program}), 200

    return app
