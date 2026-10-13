"""ACEest Fitness & Gym - Flask web application."""
from flask import Flask, jsonify, request

PROGRAMS = {
    "Fat Loss (FL)": {"factor": 22},
    "Muscle Gain (MG)": {"factor": 35},
    "Beginner (BG)": {"factor": 26},
}

CLIENTS = {}


def estimate_calories(weight, program):
    if program not in PROGRAMS:
        raise ValueError(f"Unknown program: {program}")
    if weight is None or weight <= 0:
        raise ValueError("weight must be positive")
    return round(weight * PROGRAMS[program]["factor"])


def calculate_bmi(height_cm, weight_kg):
    if height_cm is None or height_cm <= 0:
        raise ValueError("height must be positive")
    if weight_kg is None or weight_kg <= 0:
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


def create_app():
    app = Flask(__name__)

    @app.route("/")
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/programs", methods=["GET"])
    def programs():
        return jsonify(
            [{"name": n, "factor": d["factor"]} for n, d in PROGRAMS.items()]
        ), 200

    @app.route("/clients", methods=["POST"])
    def create_client():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        program = data.get("program")
        weight = data.get("weight")
        height = data.get("height")
        age = data.get("age")

        if not name:
            return jsonify({"error": "name is required"}), 400
        if program not in PROGRAMS:
            return jsonify({"error": "unknown program"}), 400
        if not isinstance(weight, (int, float)) or weight <= 0:
            return jsonify({"error": "weight must be positive"}), 400
        if height is not None and (not isinstance(height, (int, float)) or height <= 0):
            return jsonify({"error": "height must be positive"}), 400

        calories = estimate_calories(weight, program)
        client = {
            "name": name,
            "age": age,
            "height": height,
            "weight": weight,
            "program": program,
            "calories": calories,
        }
        CLIENTS[name] = client
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

    @app.route("/bmi", methods=["POST"])
    def bmi():
        data = request.get_json(silent=True) or {}
        height = data.get("height")
        weight = data.get("weight")
        try:
            value = calculate_bmi(height, weight)
        except (ValueError, TypeError):
            return jsonify({"error": "height and weight must be positive"}), 400
        return jsonify({"bmi": value, "category": bmi_category(value)}), 200

    @app.route("/calories", methods=["POST"])
    def calories():
        data = request.get_json(silent=True) or {}
        weight = data.get("weight")
        program = data.get("program")
        try:
            value = estimate_calories(weight, program)
        except (ValueError, TypeError) as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"calories": value, "program": program}), 200

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
