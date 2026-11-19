from app.main import APP_VERSION, app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert data.get("service") == "Beauty Studio API"


def test_version():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": APP_VERSION}


def test_create_booking_schema_validation():
    # Перевірка валідації вхідних даних Pydantic
    response = client.post("/api/bookings", json={})
    assert response.status_code == 422


def test_metrics_endpoint():
    # Робимо запит для генерації метрики
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text


def test_slow_endpoint():
    response = client.get("/api/slow?delay=0.01")
    assert response.status_code == 200
    assert response.json().get("status") == "delayed"
