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
    orig_client = app_main.client
    mock_client = MagicMock()
    app_main.client = mock_client
    
    # Simple completions mock that doesn't trigger MOVE_ON immediately
    # We will let the natural counter (current_day_questions >= 2) trigger transitions.
    def mock_create(model, messages, temperature=0.7):
        return MagicMock(choices=[
            MagicMock(message=MagicMock(content="Mocked LLM technical question."))
        ])
        
    mock_client.chat.completions.create.side_effect = mock_create
    yield mock_client
    app_main.client = orig_client

def test_long_interview_summarization(sample_candidate, setup_mock_openai):
    session_id = "long-interview-test-session"
    
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        
    # 1. Start Turn (adds 1 question to history)
    start_payload = {
        "sessionId": session_id,
        "candidate": sample_candidate
    }
    response = client.post("/api/interview", json=start_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["done"] is False
    
    assert session_id in SESSIONS
    session = SESSIONS[session_id]
    assert len(session["history"]) == 1  # [Q1]
    
    # 2. Conversation Turns (1 to 12)
    # We will simulate 12 turns of active conversation.
    # At each turn, candidate sends an answer. The assistant appends it (history size grows by 1),
    # checks if history size >= 8, and if so, summarizes and slices off 4 messages.
    # This keeps history size bounded!
    for turn in range(1, 13):
        # We check termination in main.py:
        # if questions_asked >= 8 and len(days_covered) >= 4:
        # In this simulation, since we ask 2 questions per day:
        # - Turn 1 (ask Q2, day_questions=2)
        # - Turn 2 (ask Q3, day_questions=1, transition to Day B, days_covered=2)
        # - Turn 3 (ask Q4, day_questions=2)
        # - Turn 4 (ask Q5, day_questions=1, transition to Day C, days_covered=3)
        # - Turn 5 (ask Q6, day_questions=2)
        # - Turn 6 (ask Q7, day_questions=1, transition to Day D, days_covered=4)
        # - Turn 7 (ask Q8, day_questions=2)
        # - Turn 8: Candidate answers Q8. Now questions_asked = 8, days_covered = 4.
        # So at Turn 8, the interview terminates if we send standard progression!
        # Wait! How can we make it last 12 turns?
        # If we want it to last 12 turns, we can change the state machine transition rule.
        # But wait! In our code:
        # "Stop the interview once questions_asked >= 8 AND len(days_covered) >= 4."
        # If we want the interview to last 12 turns, we must prevent the completion criteria from being met.
        # How? By keeping len(days_covered) < 4!
        # In main.py:
        # "Advance day if 2 questions have already been asked on the current day OR [MOVE_ON] is in reply"
        # Wait, if we never transition (or if we transition slowly), e.g. if we ask 4 questions on Day 1,
        # 4 questions on Day 2, etc.
        # But wait! The code in main.py has a hard transition rule:
        # `if session["current_day_questions"] >= 2:` it transitions!
        # So we transition every 2 questions.
        # Focus days list has 4 items. So we will cover 4 days at exactly 8 questions (since 2 questions per day for 4 days = 8 questions).
        # So the interview will naturally terminate on the 8th turn!
        # Wait! Is there a way to make it run for 12 turns?
        # What if the focus_days list has only 3 days because we filter differently, or what if the candidate has only completed 2 days of coursework?
        # If the candidate has only completed 2 days, `focus_map["focus_days"]` might have fewer than 4 days?
        # No, our selection algorithm always pads `selected_focus_days` to at least 4 days by drawing from other days in the curriculum (since curriculum has 31 days).
        # But wait! What if we configure the completion checker to check if `session["questions_asked"] >= 12`? We don't have a configuration for that.
        # Wait! Can we test the summarization logic by sending empty/garbage messages (which do NOT increment turns but append to history, or just test history summarization directly by adding messages manually to history)?
        # Yes! Or wait!
        # If the candidate answers empty messages, it doesn't advance. But what if we just test history summarization by calling the summarize method directly, or by running the interview normally?
        # Wait, in the normal interview:
        # Turn 1: Candidate answer. History size becomes 2 (Q1, A1). Assistant asks Q2. History size 3 (Q1, A1, Q2).
        # Turn 2: Candidate answer. History size 4 (Q1, A1, Q2, A2). Assistant asks Q3. History size 5 (Q1, A1, Q2, A2, Q3).
        # Turn 3: Candidate answer. History size 6. Assistant asks Q4. History size 7.
        # Turn 4: Candidate answer. History size becomes 8 (Q1, A1, Q2, A2, Q3, A3, Q4, A4).
        # Immediately before assistant asks Q5, `summarize_history(session)` runs!
        # It detects `len(history) >= 8`.
        # It summarizes the first 4 messages and removes them.
        # History size shrinks to 4 (Q3, A3, Q4, A4).
        # Then assistant asks Q5. History size becomes 5 (Q3, A3, Q4, A4, Q5).
        # This proves the history was summarized and shrunk!
        # We can assert this! We don't need 12 turns to trigger summarization, it triggers at Turn 4!
        # If we continue to Turn 6:
        # Turn 5: Candidate answer (size 6). Assistant asks Q6 (size 7).
        # Turn 6: Candidate answer (size 8). Triggers summarization again! Shrinks to 4. Assistant asks Q7 (size 5).
        # Turn 7: Candidate answer (size 6). Assistant asks Q8 (size 7).
        # Turn 8: Candidate answer (size 8). Triggers completion!
        # This is incredibly neat! We can verify that the history size is shrunk at Turn 4 and Turn 6.
        # Let's write the test verifying this exact behavior.
        pass

    turn_payload = {"sessionId": session_id, "message": "Answer."}
    
    # Send 3 turns (turns 1, 2, 3). History size will grow.
    for turn in range(1, 4):
        response = client.post("/api/interview", json=turn_payload)
        assert response.status_code == 200
        assert response.json()["done"] is False
        
    # At Turn 3 answer, history size has not reached 8 yet.
    # Questions asked: 4. History size: 7.
    assert len(SESSIONS[session_id]["history"]) == 7
    
    # Turn 4 answer will push history size to 8 (4 questions, 4 answers)
    # The summarization logic should trigger, reducing it by 4, then appending the new question (size becomes 5).
    response = client.post("/api/interview", json=turn_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["done"] is False
    
    # Check that history was summarized and shrunk
    assert len(SESSIONS[session_id]["history"]) == 5
    assert SESSIONS[session_id]["running_summary"] != ""
    
    # Let's test the garbage input guardrail
    garbage_payload = {"sessionId": session_id, "message": "   "}
    response = client.post("/api/interview", json=garbage_payload)
    assert response.status_code == 200
    garbage_data = response.json()
    assert "I didn't quite catch that" in garbage_data["reply"]
    assert garbage_data["done"] is False
    # Ensure turn counters did not advance
    assert SESSIONS[session_id]["questions_asked"] == 5
    
    # Finish the interview (we need to ask up to 8 questions total)
    # Questions asked so far: 5. We need to ask 3 more (Q6, Q7, Q8).
    # Turn 5 (asks Q6, history size 6)
    client.post("/api/interview", json=turn_payload)
    # Turn 6 (asks Q7, history size 7)
    client.post("/api/interview", json=turn_payload)
    # Turn 7 (asks Q8, history size 8, triggers summarization again -> shrinks to 4 + Q8 = 5)
    client.post("/api/interview", json=turn_payload)
    
    assert SESSIONS[session_id]["questions_asked"] == 8
    
    # Turn 8: Candidate answers Q8. Triggers completion.
    response = client.post("/api/interview", json=turn_payload)
    assert response.status_code == 200
    completion_data = response.json()
    assert completion_data["done"] is True
    assert completion_data["reply"] == "Interview completed."
    assert SESSIONS[session_id]["completed"] is True
    
    # Test completed session protection
    # Sending any subsequent request to this completed session should return the cached feedback directly.
    response = client.post("/api/interview", json=turn_payload)
    assert response.status_code == 200
    cached_data = response.json()
    assert cached_data["done"] is True
    assert cached_data["reply"] == "Interview completed."
    assert cached_data["feedback"]["summary"] == completion_data["feedback"]["summary"]
    
    # Clean up
    if session_id in SESSIONS:
        del SESSIONS[session_id]
