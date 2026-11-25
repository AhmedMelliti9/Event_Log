def test_ingest_valid_event_returns_201(client):
    payload = {
        "service_name": "auth-service",
        "event_type": "user_login",
        "severity": "info",
        "timestamp": "2024-01-15T10:30:00Z",
        "resource_id": "user:42",
        "payload": {"ip_address": "192.168.1.1", "success": True},
    }
    response = client.post("/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["service_name"] == "auth-service"
    assert data["event_type"] == "user_login"
    assert data["severity"] == "info"
    assert data["resource_id"] == "user:42"
    assert data["payload"] == {"ip_address": "192.168.1.1", "success": True}


def test_ingest_event_missing_required_field_returns_422(client):
    payload = {
        "service_name": "auth-service",
        "severity": "info",
        "timestamp": "2024-01-15T10:30:00Z",
        "resource_id": "user:42",
        "payload": {},
    }
    response = client.post("/events", json=payload)
    assert response.status_code == 422


def test_get_event_by_valid_id_returns_200(client):
    created = client.post(
        "/events",
        json={
            "service_name": "auth-service",
            "event_type": "user_login",
            "severity": "info",
            "timestamp": "2024-01-15T10:30:00Z",
            "resource_id": "user:42",
            "payload": {"method": "password"},
        },
    ).json()

    response = client.get(f"/events/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_event_by_invalid_id_format_returns_400(client):
    response = client.get("/events/not-a-valid-object-id")
    assert response.status_code == 400


def test_get_event_by_nonexistent_id_returns_404(client):
    response = client.get("/events/000000000000000000000000")
    assert response.status_code == 404


def test_query_events_by_service_name(client):
    client.post(
        "/events",
        json={
            "service_name": "auth-service",
            "event_type": "user_login",
            "severity": "info",
            "timestamp": "2024-01-15T10:00:00Z",
            "resource_id": "user:1",
            "payload": {},
        },
    )
    client.post(
        "/events",
        json={
            "service_name": "billing-service",
            "event_type": "invoice_paid",
            "severity": "info",
            "timestamp": "2024-01-15T11:00:00Z",
            "resource_id": "invoice:99",
            "payload": {},
        },
    )

    response = client.get("/events", params={"service_name": "auth-service"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["service_name"] == "auth-service"


def test_query_events_by_time_range(client):
    timestamps = [
        "2024-01-15T09:00:00Z",
        "2024-01-15T10:30:00Z",
        "2024-01-15T12:00:00Z",
    ]
    for idx, ts in enumerate(timestamps):
        client.post(
            "/events",
            json={
                "service_name": "auth-service",
                "event_type": "ping",
                "severity": "debug",
                "timestamp": ts,
                "resource_id": f"node:{idx}",
                "payload": {},
            },
        )

    response = client.get(
        "/events",
        params={
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T11:00:00Z",
        },
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["resource_id"] == "node:1"


def test_get_events_by_resource_id(client):
    client.post(
        "/events",
        json={
            "service_name": "auth-service",
            "event_type": "user_login",
            "severity": "info",
            "timestamp": "2024-01-15T10:00:00Z",
            "resource_id": "user:42",
            "payload": {},
        },
    )
    client.post(
        "/events",
        json={
            "service_name": "auth-service",
            "event_type": "user_logout",
            "severity": "info",
            "timestamp": "2024-01-15T11:00:00Z",
            "resource_id": "user:42",
            "payload": {},
        },
    )
    client.post(
        "/events",
        json={
            "service_name": "auth-service",
            "event_type": "user_login",
            "severity": "info",
            "timestamp": "2024-01-15T12:00:00Z",
            "resource_id": "user:99",
            "payload": {},
        },
    )

    response = client.get("/events/resource/user:42")
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert all(item["resource_id"] == "user:42" for item in results)
    assert results[0]["event_type"] == "user_logout"


def test_pagination_limit_and_offset(client):
    for i in range(5):
        client.post(
            "/events",
            json={
                "service_name": "auth-service",
                "event_type": "tick",
                "severity": "info",
                "timestamp": f"2024-01-15T10:0{i}:00Z",
                "resource_id": f"item:{i}",
                "payload": {"index": i},
            },
        )

    page = client.get("/events", params={"limit": 2, "offset": 1})
    assert page.status_code == 200
    items = page.json()
    assert len(items) == 2
    # Sorted descending by timestamp: indices 4, 3, 2, 1, 0 -> offset 1, limit 2 gives 3, 2
    assert [item["payload"]["index"] for item in items] == [3, 2]
