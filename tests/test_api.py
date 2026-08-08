import json
import os
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app import main as app_main
from app.main import app, SESSIONS

client = TestClient(app)

@pytest.fixture
def sample_candidate():
    candidates_file = os.path.join(os.path.dirname(__file__), "..", "candidates.json")
    assert os.path.exists(candidates_file), "candidates.json file is missing in the workspace"
    
    with open(candidates_file, "r") as f:
        data = json.load(f)
    
    return data["candidates"][0]

@pytest.fixture
def setup_mock_openai():
    orig_client = app_main.client
    mock_client = MagicMock()
    app_main.client = mock_client
    
    def mock_create(model, messages, temperature=0.7):
        return MagicMock(choices=[
            MagicMock(message=MagicMock(content="Mocked question. Let's move on. [MOVE_ON]"))
        ])
        
    mock_client.chat.completions.create.side_effect = mock_create
    yield mock_client
    app_main.client = orig_client

def test_full_interview_flow(sample_candidate, setup_mock_openai):
    session_id = "test-session-999"
    
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        
    # 1. Start Turn
    start_payload = {
        "sessionId": session_id,
        "candidate": sample_candidate
    }
    response = client.post("/api/interview", json=start_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["done"] is False
    assert "reply" in data
    assert "Welcome" in data["reply"]
    assert "Mocked" in data["reply"]
    assert "feedback" not in data or data["feedback"] is None
    
    assert session_id in SESSIONS
    assert SESSIONS[session_id]["questions_asked"] == 1
    
    # 2. Conversation Turns (1 to 7)
    for turn in range(1, 8):
        turn_payload = {
            "sessionId": session_id,
            "message": f"This is candidate answer {turn}."
        }
        response = client.post("/api/interview", json=turn_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["done"] is False
        assert "Mocked" in data["reply"]
        assert "feedback" not in data or data["feedback"] is None
        assert SESSIONS[session_id]["questions_asked"] == turn + 1
        
    # 3. Final Turn (Turn 8)
    final_payload = {
        "sessionId": session_id,
        "message": "This is candidate answer 8."
    }
    response = client.post("/api/interview", json=final_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["done"] is True
    assert data["reply"] == "Interview completed."
    
    feedback = data["feedback"]
    assert feedback is not None
    assert "summary" in feedback
    assert isinstance(feedback["strengths"], list)
    assert isinstance(feedback["gaps"], list)
    assert isinstance(feedback["next"], list)
    
    if session_id in SESSIONS:
        del SESSIONS[session_id]

def test_invalid_session():
    payload = {
        "sessionId": "non-existent-session-id",
        "message": "Hello, is anyone there?"
    }
    response = client.post("/api/interview", json=payload)
    assert response.status_code == 400
    assert "No active session found" in response.json()["detail"]

def test_invalid_payload():
    payload = {
        "sessionId": "some-session-id"
    }
    response = client.post("/api/interview", json=payload)
    assert response.status_code == 400
    assert "Invalid request" in response.json()["detail"]
