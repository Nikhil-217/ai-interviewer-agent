import json
import os
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app import main as app_main
from app.main import app, SESSIONS

client = TestClient(app)

@pytest.fixture
def load_candidates():
    path = os.path.join(os.path.dirname(__file__), "..", "candidates.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["candidates"]

@pytest.fixture
def setup_mock_openai():
    orig_client = app_main.client
    mock_client = MagicMock()
    app_main.client = mock_client
    
    def mock_create(model, messages, temperature=0.7, response_format=None):
        # Check if it's the final feedback generation
        is_feedback = False
        for msg in messages:
            if msg["role"] == "system" and ("structured feedback" in msg["content"] or "expert technical interviewer" in msg["content"]):
                is_feedback = True
                break
                
        if is_feedback:
            raw_json = json.dumps({
                "overall_score": 7,
                "concise_interviewer_summary": "Completed technical interview with standard results.",
                "strengths": ["Demonstrated clean design of pipelines on Day 1"],
                "weaknesses": ["Struggled to explain metrics on Day 29"],
                "topics_mastered": ["Day 1: Pipelines"],
                "topics_needing_review": ["Day 29: Metrics"],
                "recommended_next_steps": ["Review objectives on Day 29"],
                "per_topic_performance": {"Day 1": 8, "Day 29": 4}
            })
            return MagicMock(choices=[
                MagicMock(message=MagicMock(content=raw_json))
            ])
            
        # Standard interview question mock
        return MagicMock(choices=[
            MagicMock(message=MagicMock(content="Mocked LLM technical question. [MOVE_ON]"))
        ])
        
    mock_client.chat.completions.create.side_effect = mock_create
    yield mock_client
    app_main.client = orig_client

def test_all_candidates_compliance(load_candidates, setup_mock_openai):
    """
    1. Runs a complete interview programmatically for every candidate in candidates.json.
    2. Asserts for each run: questions_asked >= 8, days_covered >= 4, final response has done: true,
       feedback has 4 required fields, and every intermediate response has done: false and non-empty reply.
    """
    for idx, candidate in enumerate(load_candidates):
        session_id = f"compliance-session-{candidate['member']['id']}-{idx}"
        
        if session_id in SESSIONS:
            del SESSIONS[session_id]
            
        # Start turn
        start_payload = {
            "sessionId": session_id,
            "candidate": candidate
        }
        response = client.post("/api/interview", json=start_payload)
        assert response.status_code == 200, f"Start turn failed for candidate {candidate['member']['id']}"
        data = response.json()
        assert data["done"] is False
        assert data["reply"].strip() != ""
        assert data.get("feedback") is None
        
        # Loop conversations
        turn_payload = {"sessionId": session_id, "message": "Answer to question."}
        while True:
            response = client.post("/api/interview", json=turn_payload)
            assert response.status_code == 200
            data = response.json()
            
            if data["done"] is True:
                # Final response assertions
                assert "completed" in data["reply"] or "Interview" in data["reply"]
                feedback = data["feedback"]
                assert feedback is not None
                assert isinstance(feedback["concise_interviewer_summary"], str)
                assert isinstance(feedback["strengths"], list)
                assert isinstance(feedback["weaknesses"], list)
                assert isinstance(feedback["recommended_next_steps"], list)
                
                # Check session state assertions
                session_state = SESSIONS[session_id]
                assert session_state["questions_asked"] >= 8
                assert len(session_state["days_covered"]) >= 4
                break
            else:
                # Intermediate response assertions
                assert data["reply"].strip() != ""
                assert data.get("feedback") is None
                
        # Clean up session
        if session_id in SESSIONS:
            del SESSIONS[session_id]

def test_malformed_request_body():
    """
    Verify malformed request payloads return validation error codes.
    """
    # Send empty body
    response = client.post("/api/interview", content="")
    assert response.status_code in [400, 422]
    
    # Send invalid fields (e.g. integer instead of string sessionId)
    payload = {
        "sessionId": 12345,
        "message": "Hello"
    }
    response = client.post("/api/interview", json=payload)
    assert response.status_code in [400, 422]

def test_missing_session_id(load_candidates):
    """
    Verify request with missing sessionId returns validation error.
    """
    candidate = load_candidates[0]
    payload = {
        "candidate": candidate
    }
    response = client.post("/api/interview", json=payload)
    assert response.status_code in [400, 422]

def test_sparse_candidate_fallback(setup_mock_openai):
    """
    Verify candidate with very few or zero completed missions defaults correctly without crash.
    """
    sparse_candidate = {
        "member": {
            "id": "CAND-SPARSE",
            "name": "Sparse Candidate",
            "jobRole": "AI Engineer",
            "yearsExperience": 1,
            "education": "BS Computer Science",
            "status": "active"
        },
        "missions": [], # No missions completed
        "signals": {
            "commitDays": 0,
            "missionsCompleted": 0,
            "missionsFirstTry": 0
        }
    }
    
    session_id = "sparse-candidate-session"
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        
    # Start turn should run focus map which defaults correctly
    start_payload = {
        "sessionId": session_id,
        "candidate": sparse_candidate
    }
    response = client.post("/api/interview", json=start_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["done"] is False
    
    # Confirm it covered general/fallback curriculum days
    session = SESSIONS[session_id]
    assert len(session["focus_map"]["focus_days"]) >= 4
    
    if session_id in SESSIONS:
        del SESSIONS[session_id]

def test_concurrent_sessions_isolation(load_candidates, setup_mock_openai):
    """
    Verify multiple sessions running in parallel remain isolated without variable leaks.
    """
    candidate_a = load_candidates[0] # Sarah Johnson
    candidate_b = load_candidates[1] # Michael Chen
    
    session_id_a = "concurrent-session-a"
    session_id_b = "concurrent-session-b"
    
    if session_id_a in SESSIONS:
        del SESSIONS[session_id_a]
    if session_id_b in SESSIONS:
        del SESSIONS[session_id_b]
        
    # 1. Start Session A
    response_a = client.post("/api/interview", json={"sessionId": session_id_a, "candidate": candidate_a})
    assert response_a.status_code == 200
    
    # 2. Start Session B
    response_b = client.post("/api/interview", json={"sessionId": session_id_b, "candidate": candidate_b})
    assert response_b.status_code == 200
    
    # 3. Interleave conversation messages
    payload_a = {"sessionId": session_id_a, "message": "Answer A"}
    payload_b = {"sessionId": session_id_b, "message": "Answer B"}
    
    # Send alternate requests
    for _ in range(3):
        res_a = client.post("/api/interview", json=payload_a)
        assert res_a.status_code == 200
        res_b = client.post("/api/interview", json=payload_b)
        assert res_b.status_code == 200
        
    # Verify isolation
    session_a = SESSIONS[session_id_a]
    session_b = SESSIONS[session_id_b]
    
    assert session_a["candidate"]["member"]["id"] == candidate_a["member"]["id"]
    assert session_b["candidate"]["member"]["id"] == candidate_b["member"]["id"]
    
    # Check that history logs correspond to correct messages
    assert any("Answer A" in str(msg) for msg in session_a["history"])
    assert not any("Answer B" in str(msg) for msg in session_a["history"])
    
    assert any("Answer B" in str(msg) for msg in session_b["history"])
    assert not any("Answer A" in str(msg) for msg in session_b["history"])
    
    # Clean up
    if session_id_a in SESSIONS:
        del SESSIONS[session_id_a]
    if session_id_b in SESSIONS:
        del SESSIONS[session_id_b]
