import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield

def test_root_endpoint():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "version" in data

def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/v1/settings/health")
        assert response.status_code == 200
        data = response.json()
        assert "ffmpeg" in data
        assert "whisper" in data
        assert "ollama" in data
        assert "diarization" in data

def test_list_meetings_empty():
    with TestClient(app) as client:
        response = client.get("/api/v1/meetings")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
