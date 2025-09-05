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
    # Purchase a seat via /api/orders
    purchase = client.post(
        "/api/orders",
        json={"event_id": 1, "seat_ids": [1]},
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert purchase.status_code in (200, 409)
    if purchase.status_code == 200:
        order_id = purchase.json()["order_id"]
        qr = client.get(f"/tickets/{order_id}/qrcode.png")
        assert qr.status_code == 200
        assert qr.headers["content-type"] == "image/png"
