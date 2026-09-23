from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Beauty Studio API"}


def test_create_booking_schema_validation():
    # Перевірка валідації вхідних даних Pydantic
    response = client.post("/api/bookings", json={})
    assert response.status_code == 422
