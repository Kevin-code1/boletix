from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_get_events():
    response = client.get("/api/events")
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    assert len(events) >= 1


def test_login_and_purchase():
    # Login
    response = client.post(
        "/api/login",
        json={"email": "demo@example.com", "password": "demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    # Purchase a seat
    purchase = client.post("/api/events/1/seats/1/purchase")
    # puede devolver 409 si otro test ya lo vendió
    assert purchase.status_code in (200, 409)
    if purchase.status_code == 200:
        order_id = purchase.json()["order_id"]
        qr = client.get(f"/tickets/{order_id}/qrcode.png")
        assert qr.status_code == 200
        assert qr.headers["content-type"] == "image/png"
