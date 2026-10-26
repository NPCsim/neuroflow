from fastapi import status


def test_health_check_endpoint(client):
    """Test that /health returns 200, valid JSON schema, and database connected status."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "NeuroFlow API"
    assert data["version"] == "1.0.0"
    assert data["database"] == "connected"
    assert "timestamp" in data


def test_root_endpoint(client):
    """Test that / returns 200 and basic API navigation links."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["app"] == "NeuroFlow API"
    assert data["status"] == "online"
    assert data["health"] == "/health"
    assert data["docs"] == "/docs"

