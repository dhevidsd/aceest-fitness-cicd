"""ACEest Fitness & Gym - Flask web application (latest release, v2.0.0).

Version history (snapshots kept in ``versions/``):
    1.0.0 - health, programs and calorie estimation API.
    1.1.0 - client management and BMI calculation.
    2.0.0 - version endpoint metadata, client deletion and workout logging.
"""
import os
import socket

from flask import Flask, jsonify, request

APP_NAME = "ACEest Fitness & Gym"
VERSION = "2.0.0"

PROGRAMS = {
    "Fat Loss (FL)": {"factor": 22},
    "Muscle Gain (MG)": {"factor": 35},
    "Beginner (BG)": {"factor": 26},
}

CLIENTS = {}
WORKOUTS = {}


def estimate_calories(weight, program):
    if program not in PROGRAMS:
        raise ValueError(f"Unknown program: {program}")
    if not isinstance(weight, (int, float)) or weight <= 0:
        raise ValueError("weight must be positive")
    return round(weight * PROGRAMS[program]["factor"])


def calculate_bmi(height_cm, weight_kg):
    if not isinstance(height_cm, (int, float)) or height_cm <= 0:
        raise ValueError("height must be positive")
    if not isinstance(weight_kg, (int, float)) or weight_kg <= 0:
        raise ValueError("weight must be positive")
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m * height_m), 1)


def bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def reset_store():
    CLIENTS.clear()
    WORKOUTS.clear()


def version_info():
    """Runtime metadata used to tell deployment tracks apart (blue/green, canary...)."""
    return {
        "app": APP_NAME,
        "version": VERSION,
        "track": os.environ.get("DEPLOYMENT_TRACK", "stable"),
        "hostname": socket.gethostname(),
    }


def _validate_client(data):
    name = (data.get("name") or "").strip()
    program = data.get("program")
    weight = data.get("weight")
    height = data.get("height")

    if not name:
        return None, "name is required"
    if program not in PROGRAMS:
        return None, "unknown program"
    if not isinstance(weight, (int, float)) or weight <= 0:
        return None, "weight must be positive"
    if height is not None and (not isinstance(height, (int, float)) or height <= 0):
        return None, "height must be positive"

    return {
        "name": name,
        "age": data.get("age"),
        "height": height,
        "weight": weight,
        "program": program,
        "calories": estimate_calories(weight, program),
    }, None


def _validate_workout(data):
    workout_type = (data.get("type") or "").strip()
    duration = data.get("duration_min")
    if not workout_type:
        return None, "type is required"
    if not isinstance(duration, (int, float)) or duration <= 0:
        return None, "duration_min must be positive"
    return {"type": workout_type, "duration_min": duration, "notes": data.get("notes", "")}, None


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
        return jsonify(version_info()), 200

    @app.route("/programs", methods=["GET"])
    def programs():
        return jsonify(
            [{"name": n, "factor": d["factor"]} for n, d in PROGRAMS.items()]
        ), 200

    @app.route("/clients", methods=["POST"])
    def create_client():
        client, error = _validate_client(request.get_json(silent=True) or {})
        if error:
            return jsonify({"error": error}), 400
        CLIENTS[client["name"]] = client
        return jsonify(client), 201

    @app.route("/clients", methods=["GET"])
    def list_clients():
        return jsonify(list(CLIENTS.values())), 200

    @app.route("/clients/<name>", methods=["GET"])
    def get_client(name):
        client = CLIENTS.get(name)
        if client is None:
            return jsonify({"error": "client not found"}), 404
        return jsonify(client), 200

    @app.route("/clients/<name>", methods=["DELETE"])
    def delete_client(name):
        if CLIENTS.pop(name, None) is None:
            return jsonify({"error": "client not found"}), 404
        WORKOUTS.pop(name, None)
        return "", 204

    @app.route("/clients/<name>/workouts", methods=["POST"])
    def add_workout(name):
        if name not in CLIENTS:
            return jsonify({"error": "client not found"}), 404
        workout, error = _validate_workout(request.get_json(silent=True) or {})
        if error:
            return jsonify({"error": error}), 400
        WORKOUTS.setdefault(name, []).append(workout)
        return jsonify(workout), 201

    @app.route("/clients/<name>/workouts", methods=["GET"])
    def list_workouts(name):
        if name not in CLIENTS:
            return jsonify({"error": "client not found"}), 404
        items = WORKOUTS.get(name, [])
        total = sum(w["duration_min"] for w in items)
        return jsonify({"client": name, "workouts": items, "total_minutes": total}), 200

    @app.route("/bmi", methods=["POST"])
    def bmi():
        data = request.get_json(silent=True) or {}
        try:
            value = calculate_bmi(data.get("height"), data.get("weight"))
        except ValueError:
            return jsonify({"error": "height and weight must be positive"}), 400
        return jsonify({"bmi": value, "category": bmi_category(value)}), 200

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


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
