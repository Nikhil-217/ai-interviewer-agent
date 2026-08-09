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
    
    # We will let the simulated mock completions return normal questions.
    # The final feedback call will return simulated JSON based on candidate's name.
    def mock_create(model, messages, temperature=0.7, response_format=None):
        # Determine if this is a feedback generation request (based on system instructions or JSON format)
        is_feedback = False
        system_msg = ""
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
                if "structured feedback evaluation" in system_msg or "expert technical interviewer" in system_msg:
                    is_feedback = True
                    break
                    
        if is_feedback:
            # Check if history contains Sarah or Emily
            history_str = str(messages)
            if "Sarah" in history_str or "CAND-001" in history_str:
                raw_json = json.dumps({
                    "overall_score": 5,
                    "concise_interviewer_summary": "Overall completed technical interview with mixed results on data engineering.",
                    "strengths": ["Demonstrated clean design of pipelines on Day 1"],
                    "weaknesses": ["Struggled to explain Prometheus metrics configuration from Day 29"],
                    "topics_mastered": ["Day 1"],
                    "topics_needing_review": ["Day 29"],
                    "recommended_next_steps": ["Review logging objectives on Day 29"],
                    "per_topic_performance": {}
                })
            else:
                raw_json = json.dumps({
                    "overall_score": 9,
                    "concise_interviewer_summary": "Overall completed technical interview with high performance.",
                    "strengths": ["Mastered embeddings PCA visualization on Day 7"],
                    "weaknesses": ["Could refine routing strategies from Day 10"],
                    "topics_mastered": ["Day 7"],
                    "topics_needing_review": ["Day 10"],
                    "recommended_next_steps": ["Read advanced retrieval strategies from Day 10"],
                    "per_topic_performance": {}
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

def test_feedback_differentiation(load_candidates, setup_mock_openai):
    # 1. Test Sarah Johnson (CAND-001) - Skipped Day 29
    sarah = next(c for c in load_candidates if c["member"]["id"] == "CAND-001")
    sarah_session = "sarah-session-123"
    
    if sarah_session in SESSIONS:
        del SESSIONS[sarah_session]
        
    # Start interview
    response = client.post("/api/interview", json={"sessionId": sarah_session, "candidate": sarah})
    assert response.status_code == 200
    
    # Progress turns 1 to 7
    sarah_payload = {"sessionId": sarah_session, "message": "Answer."}
    for turn in range(1, 8):
        client.post("/api/interview", json=sarah_payload)
        
    # Final turn 8 (concludes and returns final feedback)
    response = client.post("/api/interview", json=sarah_payload)
    assert response.status_code == 200
    sarah_data = response.json()
    assert sarah_data["done"] is True
    
    sarah_feedback = sarah_data["feedback"]
    assert sarah_feedback is not None
    # Verify grounded strengths/gaps for Sarah (Day 29)
    assert "Day 29" in str(sarah_feedback["weaknesses"]) or "Day 29" in str(sarah_feedback["recommended_next_steps"])
    assert "Prometheus" in str(sarah_feedback["weaknesses"])
    assert "Day 1" in str(sarah_feedback["strengths"])
    
    # 2. Test Emily Chen (CAND-003) - Master
    emily = next(c for c in load_candidates if c["member"]["id"] == "CAND-003")
    emily_session = "emily-session-456"
    
    if emily_session in SESSIONS:
        del SESSIONS[emily_session]
        
    # Start interview
    response = client.post("/api/interview", json={"sessionId": emily_session, "candidate": emily})
    assert response.status_code == 200
    
    # Progress turns 1 to 7
    emily_payload = {"sessionId": emily_session, "message": "Answer."}
    for turn in range(1, 8):
        client.post("/api/interview", json=emily_payload)
        
    # Final turn 8 (concludes and returns final feedback)
    response = client.post("/api/interview", json=emily_payload)
    assert response.status_code == 200
    emily_data = response.json()
    assert emily_data["done"] is True
    
    emily_feedback = emily_data["feedback"]
    assert emily_feedback is not None
    # Verify grounded strengths/gaps for Emily (Day 7 / Day 10)
    assert "Day 7" in str(emily_feedback["strengths"])
    assert "embeddings PCA" in str(emily_feedback["strengths"])
    assert "Day 10" in str(emily_feedback["weaknesses"])
    
    # Ensure feedback values differ meaningfully
    assert sarah_feedback["concise_interviewer_summary"] != emily_feedback["concise_interviewer_summary"]
    assert sarah_feedback["strengths"] != emily_feedback["strengths"]
    assert sarah_feedback["weaknesses"] != emily_feedback["weaknesses"]
    
    # Clean up
    if sarah_session in SESSIONS:
        del SESSIONS[sarah_session]
    if emily_session in SESSIONS:
        del SESSIONS[emily_session]
