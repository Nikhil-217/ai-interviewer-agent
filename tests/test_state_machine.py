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
    path = os.path.join(os.path.dirname(__file__), "..", "candidates.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["candidates"][0]

@pytest.fixture
def setup_mock_openai():
    # Store original client
    orig_client = app_main.client
    
    # Create mock client and mock response
    mock_client = MagicMock()
    app_main.client = mock_client
    
    # We will configure side_effect to return different answers
    # to simulate the flow of questions.
    def mock_create(model, messages, temperature=0.7, **kwargs):
        import re
        # Inspect system prompt to see which day we are probing
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        
        # Extract Day from system msg if present
        day_match = re.search(r"Day\s+(\d+)", system_msg)
        if day_match:
            day_num = day_match.group(1)
            # First question on that day
            return MagicMock(choices=[
                MagicMock(message=MagicMock(content=f"Mocked initial question for Day {day_num}."))
            ])
            
        # If we are evaluating final feedback, mock valid JSON to prevent fallback
        if "evaluating a candidate" in system_msg:
            return MagicMock(choices=[
                MagicMock(message=MagicMock(content='{"overall_score": 8, "concise_interviewer_summary": "Great", "strengths": ["Good"], "weaknesses": [], "topics_mastered": ["Day 8"], "topics_needing_review": [], "recommended_next_steps": [], "per_topic_performance": {"Day 8": 8}}'))
            ])
            
        # If it's a follow-up, let's signal MOVE_ON
        # In a real conversation, the history will have some role/content
        # Let's return MOVE_ON to test day transition
        return MagicMock(choices=[
            MagicMock(message=MagicMock(content="Mocked question. Let's move on. [MOVE_ON]"))
        ])
        
    mock_client.chat.completions.create.side_effect = mock_create
    
    yield mock_client
    
    # Restore original client
    app_main.client = orig_client

def test_state_machine_flow(sample_candidate, setup_mock_openai):
    session_id = "state-machine-test-session"
    
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
    assert "Welcome" in data["reply"]
    assert "Day 29" in data["reply"] or "Day" in data["reply"] or "Mocked" in data["reply"]
    
    # Verify initial session state
    assert session_id in SESSIONS
    session = SESSIONS[session_id]
    assert session["questions_asked"] == 1
    assert len(session["days_covered"]) == 1
    assert session["current_focus_index"] == 0
    assert session["current_day_questions"] == 1
    
    # 2. Conversation Turns
    for turn in range(1, 8):
        turn_payload = {
            "sessionId": session_id,
            "message": f"Answer to question {turn}."
        }
        response = client.post("/api/interview", json=turn_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["done"] is False
        assert "Mocked" in data["reply"]
        assert SESSIONS[session_id]["questions_asked"] == turn + 1
        
    # 3. Final Turn (the candidate responds to the 8th question)
    final_payload = {
        "sessionId": session_id,
        "message": "Answer to question 8."
    }
    response = client.post("/api/interview", json=final_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["done"] is True
    assert data["reply"] == "Interview completed."
    
    feedback = data["feedback"]
    assert feedback is not None
    assert "overall_score" in feedback
    print("DEBUG FEEDBACK:", feedback)
    assert len(feedback["strengths"]) > 0
    
    # Clean up
    if session_id in SESSIONS:
        del SESSIONS[session_id]

def test_clueless_response_transitions_immediately(sample_candidate, setup_mock_openai):
    session_id = "clueless-transition-test-session"
    
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        
    # 1. Start Turn (initial day is assigned)
    start_payload = {
        "sessionId": session_id,
        "candidate": sample_candidate
    }
    response = client.post("/api/interview", json=start_payload)
    assert response.status_code == 200
    
    assert session_id in SESSIONS
    session = SESSIONS[session_id]
    assert session["questions_asked"] == 1
    assert session["current_day_questions"] == 1
    day_1 = session["days_covered"][0]
    
    # 2. Candidate responds with "i dont know" to the initial question
    turn_payload = {
        "sessionId": session_id,
        "message": "i dont know"
    }
    response = client.post("/api/interview", json=turn_payload)
    assert response.status_code == 200
    
    # Verify that the session has immediately transitioned to a new day
    assert session["questions_asked"] == 2
    assert session["current_day_questions"] == 1  # Becomes 1 after the new day's initial question is asked
    assert len(session["days_covered"]) == 2
    assert session["days_covered"][1] != day_1
    
    # Clean up
    if session_id in SESSIONS:
        del SESSIONS[session_id]
