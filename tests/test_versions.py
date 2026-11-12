"""Tests for v2.0 features and the historical version snapshots."""
import pytest

import ACEest_Fitness as latest
from versions import ACEest_Fitness_v1_0 as v1_0
from versions import ACEest_Fitness_v1_1 as v1_1


@pytest.fixture(autouse=True)
def _clean_store():
    latest.reset_store()
    v1_1.reset_store()
    yield
    latest.reset_store()
    v1_1.reset_store()


def _client(module):
    app = module.create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.mark.parametrize(
    "module,expected",
    [(v1_0, "1.0.0"), (v1_1, "1.1.0"), (latest, "2.0.0")],
)
def test_version_endpoint_and_header(module, expected, monkeypatch):
    monkeypatch.setenv("DEPLOYMENT_TRACK", "canary")
    resp = _client(module).get("/version")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["version"] == expected
    assert body["track"] == "canary"
    assert body["hostname"]
    assert resp.headers["X-App-Version"] == expected


@pytest.mark.parametrize("module", [v1_0, v1_1, latest])
def test_health_all_versions(module):
    resp = _client(module).get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


@pytest.mark.parametrize("module", [v1_0, v1_1, latest])
def test_calories_all_versions(module):
    http = _client(module)
    ok = http.post("/calories", json={"weight": 70, "program": "Fat Loss (FL)"})
    assert ok.get_json()["calories"] == 1540
    bad = http.post("/calories", json={"weight": "x", "program": "Fat Loss (FL)"})
    assert bad.status_code == 400
    assert http.get("/programs").status_code == 200


def test_v1_0_has_no_client_api():
    assert _client(v1_0).get("/clients").status_code == 404


def test_v1_1_clients_and_bmi():
    http = _client(v1_1)
    created = http.post("/clients", json={"name": "Asha", "weight": 60, "program": "Beginner (BG)"})
    assert created.status_code == 201
    assert http.get("/clients").get_json()[0]["calories"] == 1560
    assert http.get("/clients/Asha").status_code == 200
    assert http.get("/clients/None").status_code == 404
    assert http.post("/clients", json={}).status_code == 400
    assert http.post("/clients", json={"name": "A", "program": "x"}).status_code == 400
    assert http.post(
        "/clients", json={"name": "A", "program": "Beginner (BG)", "weight": -1}
    ).status_code == 400
    assert http.post(
        "/clients", json={"name": "A", "program": "Beginner (BG)", "weight": 50, "height": 0}
    ).status_code == 400
    assert http.post("/bmi", json={"height": 180, "weight": 81}).get_json()["bmi"] == 25.0
    assert http.post("/bmi", json={"height": 180}).status_code == 400
    # v1.1 does not support deleting clients
    assert http.delete("/clients/Asha").status_code == 405


@pytest.mark.parametrize(
    "bmi,expected",
    [(17.0, "Underweight"), (22.0, "Normal"), (27.0, "Overweight"), (31.0, "Obese")],
)
def test_v1_1_bmi_category(bmi, expected):
    assert v1_1.bmi_category(bmi) == expected


def test_v1_1_calculate_bmi_invalid():
    with pytest.raises(ValueError):
        v1_1.calculate_bmi(170, 0)


def test_latest_rejects_invalid_height():
    http = _client(latest)
    resp = http.post(
        "/clients", json={"name": "H", "program": "Beginner (BG)", "weight": 50, "height": -5}
    )
    assert resp.status_code == 400


def test_latest_delete_client():
    http = _client(latest)
    http.post("/clients", json={"name": "Ravi", "weight": 80, "program": "Muscle Gain (MG)"})
    assert http.delete("/clients/Ravi").status_code == 204
    assert http.get("/clients/Ravi").status_code == 404
    assert http.delete("/clients/Ravi").status_code == 404


def test_latest_workouts():
    http = _client(latest)
    assert http.get("/clients/Ghost/workouts").status_code == 404
    assert http.post("/clients/Ghost/workouts", json={}).status_code == 404

    http.post("/clients", json={"name": "Meena", "weight": 60, "program": "Fat Loss (FL)"})
    assert http.post("/clients/Meena/workouts", json={"duration_min": 30}).status_code == 400
    assert http.post(
        "/clients/Meena/workouts", json={"type": "Run", "duration_min": 0}
    ).status_code == 400

    created = http.post(
        "/clients/Meena/workouts", json={"type": "Run", "duration_min": 30, "notes": "5k"}
    )
    assert created.status_code == 201
    http.post("/clients/Meena/workouts", json={"type": "Yoga", "duration_min": 45})

    body = http.get("/clients/Meena/workouts").get_json()
    assert body["total_minutes"] == 75
    assert [w["type"] for w in body["workouts"]] == ["Run", "Yoga"]
