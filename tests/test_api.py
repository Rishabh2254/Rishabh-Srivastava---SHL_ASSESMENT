"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_schema_compliance(client):
    payload = {
        "messages": [{"role": "user", "content": "I need an assessment"}]
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "recommendations" in data
    assert "end_of_conversation" in data
    assert data["recommendations"] == []
    assert isinstance(data["end_of_conversation"], bool)


def test_off_topic_refusal(client):
    payload = {
        "messages": [{"role": "user", "content": "Give me salary negotiation advice"}]
    }
    response = client.post("/chat", json=payload)
    data = response.json()
    assert data["recommendations"] == []
    assert "SHL" in data["reply"] or "cannot" in data["reply"].lower()
