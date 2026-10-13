"""Pytest suite for the ACEest Fitness & Gym Flask application."""
import pytest

from app import (
    create_app,
    estimate_calories,
    calculate_bmi,
    bmi_category,
    reset_store,
)


@pytest.fixture(autouse=True)
def _clean_store():
    reset_store()
    yield
    reset_store()


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_root_is_health(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_programs(client):
    resp = client.get("/programs")
    assert resp.status_code == 200
    data = {p["name"]: p["factor"] for p in resp.get_json()}
    assert data == {
        "Fat Loss (FL)": 22,
        "Muscle Gain (MG)": 35,
        "Beginner (BG)": 26,
    }


def test_estimate_calories():
    assert estimate_calories(80, "Muscle Gain (MG)") == 2800
    assert estimate_calories(70, "Fat Loss (FL)") == 1540


def test_estimate_calories_invalid():
    with pytest.raises(ValueError):
        estimate_calories(80, "Nope")
    with pytest.raises(ValueError):
        estimate_calories(0, "Beginner (BG)")


def test_calculate_bmi():
    assert calculate_bmi(180, 81) == 25.0


@pytest.mark.parametrize(
    "bmi,expected",
    [
        (17.0, "Underweight"),
        (18.5, "Normal"),
        (22.0, "Normal"),
        (25.0, "Overweight"),
        (29.9, "Overweight"),
        (30.0, "Obese"),
        (40.0, "Obese"),
    ],
)
def test_bmi_category(bmi, expected):
    assert bmi_category(bmi) == expected


def test_create_client_success(client):
    resp = client.post(
        "/clients",
        json={
            "name": "Ravi",
            "age": 30,
            "height": 175,
            "weight": 80,
            "program": "Muscle Gain (MG)",
        },
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "Ravi"
    assert body["calories"] == 2800


def test_create_client_missing_name(client):
    resp = client.post("/clients", json={"weight": 80, "program": "Beginner (BG)"})
    assert resp.status_code == 400


def test_create_client_unknown_program(client):
    resp = client.post("/clients", json={"name": "X", "weight": 80, "program": "Bad"})
    assert resp.status_code == 400


def test_create_client_non_positive_weight(client):
    resp = client.post(
        "/clients", json={"name": "X", "weight": 0, "program": "Beginner (BG)"}
    )
    assert resp.status_code == 400


def test_get_client_found_and_missing(client):
    client.post(
        "/clients", json={"name": "Meena", "weight": 60, "program": "Fat Loss (FL)"}
    )
    found = client.get("/clients/Meena")
    assert found.status_code == 200
    assert found.get_json()["name"] == "Meena"

    missing = client.get("/clients/Nobody")
    assert missing.status_code == 404


def test_list_clients(client):
    client.post("/clients", json={"name": "A", "weight": 70, "program": "Beginner (BG)"})
    resp = client.get("/clients")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_bmi_endpoint_success(client):
    resp = client.post("/bmi", json={"height": 180, "weight": 81})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["bmi"] == 25.0
    assert body["category"] == "Overweight"


def test_bmi_endpoint_invalid(client):
    resp = client.post("/bmi", json={"height": 0, "weight": 80})
    assert resp.status_code == 400


def test_calories_endpoint_success(client):
    resp = client.post("/calories", json={"weight": 80, "program": "Muscle Gain (MG)"})
    assert resp.status_code == 200
    assert resp.get_json()["calories"] == 2800


def test_calories_endpoint_unknown_program(client):
    resp = client.post("/calories", json={"weight": 80, "program": "Bad"})
    assert resp.status_code == 400
