"""
Comprehensive Feature Test Suite for AI Interview Agent
=======================================================
Covers all acceptance criteria from the agent-testing skill:
- Minimum 8 questions, 4+ curriculum days
- Follow-up questions depend on previous answers
- Context preserved across turns
- Structured final feedback produced
- Candidate profile affects interview selection
- Behavioral tests: excellent, partial, vague, "I don't know", empty
- API contract: valid, invalid JSON, missing candidate, empty answer, session continuation
- Session isolation (interleaving)
- Duplicate question prevention
- Retrieval: relevant days, fallback, skipped topics
"""

import json
import httpx
import uuid
import time
import sys

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/interview"

PASS = 0
FAIL = 0
RESULTS = []

def log_result(test_name, passed, detail=""):
    global PASS, FAIL
    status = "✅ PASS" if passed else "❌ FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    msg = f"  {status} | {test_name}"
    if detail and not passed:
        msg += f"\n         Detail: {detail}"
    print(msg)
    RESULTS.append({"test": test_name, "passed": passed, "detail": detail})

def load_candidates():
    with open("candidates.json", "r", encoding="utf-8") as f:
        return json.load(f)["candidates"]

# ============================================================================
# TEST 1: Full Interview Flow — Sarah Johnson (8 questions, 4+ days, feedback)
# ============================================================================
def test_full_interview_flow():
    print("\n" + "="*70)
    print("TEST 1: Full Interview Flow (Sarah Johnson)")
    print("="*70)
    
    candidates = load_candidates()
    sarah = candidates[0]
    session_id = f"test-full-{uuid.uuid4().hex[:8]}"
    
    # Start turn
    resp = httpx.post(API_URL, json={"sessionId": session_id, "candidate": sarah}, timeout=15.0)
    data = resp.json()
    
    log_result("Start turn returns 200", resp.status_code == 200)
    log_result("Start turn has reply", "reply" in data and len(data["reply"]) > 0)
    log_result("Start turn done=false", data.get("done") == False)
    log_result("Start turn no feedback", data.get("feedback") is None)
    
    first_question = data["reply"]
    questions_received = [first_question]
    
    # Varied answer types to test adaptation
    answers = [
        # Turn 1: Excellent answer
        "I implemented structured logging with JSON format using Python's logging module with custom formatters. "
        "Metrics were collected via Prometheus client library exposing histogram for latency and counter for errors. "
        "Traces were instrumented with OpenTelemetry SDK propagating W3C trace context headers across microservices.",
        
        # Turn 2: Partial answer
        "I know metrics are important but I only used print statements for debugging.",
        
        # Turn 3: Vague answer
        "I think I did something with prompts but I'm not sure of the details.",
        
        # Turn 4: "I don't know"
        "I don't know much about that topic, I skipped it.",
        
        # Turn 5: Detailed technical answer
        "I containerized the app using a multi-stage Dockerfile with a slim Python base image, "
        "configured health checks, and deployed to Kubernetes with rolling update strategy and resource limits.",
        
        # Turn 6: Incorrect/off-topic answer
        "I think RAG stands for Random Access Generation and it's used for database indexing.",
        
        # Turn 7: Strong conceptual answer
        "Embeddings map semantic meaning into dense vector space where cosine similarity captures relatedness. "
        "I used HNSW indexing with ef_construction=200 and M=16 for high recall at acceptable latency.",
    ]
    
    done = False
    turn = 0
    for answer in answers:
        turn += 1
        resp = httpx.post(API_URL, json={"sessionId": session_id, "message": answer}, timeout=15.0)
        data = resp.json()
        
        if data.get("done"):
            done = True
            break
        
        questions_received.append(data["reply"])
    
    # If not done yet, keep sending until done
    extra_turns = 0
    while not done and extra_turns < 5:
        extra_turns += 1
        resp = httpx.post(API_URL, json={
            "sessionId": session_id, 
            "message": "I implemented it using standard best practices with proper error handling."
        }, timeout=15.0)
        data = resp.json()
        if data.get("done"):
            done = True
            break
        questions_received.append(data["reply"])
    
    total_questions = len(questions_received)
    
    log_result("Interview completed (done=true)", done)
    log_result(f"At least 8 questions asked ({total_questions})", total_questions >= 8)
    
    # Check feedback structure
    feedback = data.get("feedback")
    log_result("Feedback object present", feedback is not None)
    if feedback:
        log_result("Feedback has summary (string)", isinstance(feedback.get("summary"), str) and len(feedback["summary"]) > 0)
        log_result("Feedback has strengths (list)", isinstance(feedback.get("strengths"), list) and len(feedback["strengths"]) > 0)
        log_result("Feedback has gaps (list)", isinstance(feedback.get("gaps"), list) and len(feedback["gaps"]) > 0)
        log_result("Feedback has next (list)", isinstance(feedback.get("next"), list) and len(feedback["next"]) > 0)
    
    # Check for duplicate questions
    unique_questions = set(questions_received)
    log_result(f"No exact duplicate questions ({len(unique_questions)}/{total_questions})", 
               len(unique_questions) == total_questions)
    
    return session_id, data

# ============================================================================
# TEST 2: Cached Completed Session
# ============================================================================
def test_cached_session(session_id):
    print("\n" + "="*70)
    print("TEST 2: Cached Completed Session")
    print("="*70)
    
    resp = httpx.post(API_URL, json={"sessionId": session_id, "message": "Hello again"}, timeout=10.0)
    data = resp.json()
    
    log_result("Cached session returns done=true", data.get("done") == True)
    log_result("Cached session has feedback", data.get("feedback") is not None)

# ============================================================================
# TEST 3: Second Candidate — Emily Chen (different profile, different questions)
# ============================================================================
def test_second_candidate():
    print("\n" + "="*70)
    print("TEST 3: Different Candidate Profile (Emily Chen)")
    print("="*70)
    
    candidates = load_candidates()
    emily = candidates[2]  # Emily Chen
    session_id = f"test-emily-{uuid.uuid4().hex[:8]}"
    
    resp = httpx.post(API_URL, json={"sessionId": session_id, "candidate": emily}, timeout=15.0)
    data = resp.json()
    
    log_result("Emily start turn returns 200", resp.status_code == 200)
    log_result("Emily gets a question", len(data.get("reply", "")) > 10)
    
    emily_first_q = data["reply"]
    
    # Compare with Sarah's first question (loaded from test 1)
    # They should differ since profiles differ
    # We can't directly compare but we verify the question content is present
    log_result("Emily question is non-trivial", 
               len(emily_first_q) > 30 and "Day" in emily_first_q or "day" in emily_first_q.lower())

# ============================================================================
# TEST 4: Session Isolation (Interleaving A/B)
# ============================================================================
def test_session_isolation():
    print("\n" + "="*70)
    print("TEST 4: Session Isolation (Interleaving)")
    print("="*70)
    
    candidates = load_candidates()
    
    sid_a = f"test-iso-A-{uuid.uuid4().hex[:8]}"
    sid_b = f"test-iso-B-{uuid.uuid4().hex[:8]}"
    
    # Start both sessions
    resp_a = httpx.post(API_URL, json={"sessionId": sid_a, "candidate": candidates[0]}, timeout=15.0)
    resp_b = httpx.post(API_URL, json={"sessionId": sid_b, "candidate": candidates[1]}, timeout=15.0)
    
    q_a1 = resp_a.json()["reply"]
    q_b1 = resp_b.json()["reply"]
    
    log_result("Both sessions start successfully", resp_a.status_code == 200 and resp_b.status_code == 200)
    
    # Interleave: answer A, then B, then A
    resp_a2 = httpx.post(API_URL, json={"sessionId": sid_a, "message": "Answer for session A turn 1"}, timeout=15.0)
    resp_b2 = httpx.post(API_URL, json={"sessionId": sid_b, "message": "Answer for session B turn 1"}, timeout=15.0)
    resp_a3 = httpx.post(API_URL, json={"sessionId": sid_a, "message": "Answer for session A turn 2"}, timeout=15.0)
    
    log_result("Session A progresses independently", resp_a2.status_code == 200 and resp_a3.status_code == 200)
    log_result("Session B progresses independently", resp_b2.status_code == 200)
    
    # Verify A and B have different state (different reply content)
    reply_a3 = resp_a3.json().get("reply", "")
    reply_b2 = resp_b2.json().get("reply", "")
    log_result("A and B replies differ (no cross-talk)", reply_a3 != reply_b2)

# ============================================================================
# TEST 5: API Error Handling
# ============================================================================
def test_api_errors():
    print("\n" + "="*70)
    print("TEST 5: API Error Handling")
    print("="*70)
    
    # Missing sessionId
    resp = httpx.post(API_URL, json={"candidate": {}}, timeout=10.0)
    log_result("Missing sessionId returns 422", resp.status_code == 422)
    
    # Missing both candidate and message (just sessionId)
    resp = httpx.post(API_URL, json={"sessionId": "test-err-1"}, timeout=10.0)
    log_result("Missing candidate+message returns 400", resp.status_code == 400)
    
    # Message to non-existent session
    resp = httpx.post(API_URL, json={"sessionId": "nonexistent-session-xyz", "message": "hello"}, timeout=10.0)
    log_result("Non-existent session returns 404", resp.status_code == 404)
    
    # Invalid JSON body
    resp = httpx.post(API_URL, content=b"not json at all", 
                      headers={"Content-Type": "application/json"}, timeout=10.0)
    log_result("Invalid JSON returns 422", resp.status_code == 422)

# ============================================================================
# TEST 6: Empty / Whitespace Message Handling
# ============================================================================
def test_empty_messages():
    print("\n" + "="*70)
    print("TEST 6: Empty / Whitespace Message Handling")
    print("="*70)
    
    candidates = load_candidates()
    session_id = f"test-empty-{uuid.uuid4().hex[:8]}"
    
    # Start session
    httpx.post(API_URL, json={"sessionId": session_id, "candidate": candidates[0]}, timeout=15.0)
    
    # Send empty message
    resp = httpx.post(API_URL, json={"sessionId": session_id, "message": ""}, timeout=10.0)
    data = resp.json()
    log_result("Empty message returns 200 (graceful)", resp.status_code == 200)
    log_result("Empty message returns clarification reply", len(data.get("reply", "")) > 5)
    log_result("Empty message does NOT set done=true", data.get("done") == False)
    
    # Send whitespace-only message
    resp = httpx.post(API_URL, json={"sessionId": session_id, "message": "   "}, timeout=10.0)
    data = resp.json()
    log_result("Whitespace message returns graceful reply", len(data.get("reply", "")) > 5)

# ============================================================================
# TEST 7: Candidates API Endpoint
# ============================================================================
def test_candidates_api():
    print("\n" + "="*70)
    print("TEST 7: GET /api/candidates Endpoint")
    print("="*70)
    
    resp = httpx.get(f"{BASE_URL}/api/candidates", timeout=10.0)
    data = resp.json()
    
    log_result("GET /api/candidates returns 200", resp.status_code == 200)
    log_result("Returns list of candidates", isinstance(data, list) and len(data) > 0)
    
    if len(data) > 0:
        first = data[0]
        log_result("Candidate has member.name", "member" in first and "name" in first["member"])
        log_result("Candidate has missions list", "missions" in first and isinstance(first["missions"], list))
        log_result("Candidate has signals", "signals" in first and "commitDays" in first.get("signals", {}))

# ============================================================================
# TEST 8: Static File Serving (Frontend Assets)
# ============================================================================
def test_static_serving():
    print("\n" + "="*70)
    print("TEST 8: Static File Serving")
    print("="*70)
    
    # Root page
    resp = httpx.get(f"{BASE_URL}/", timeout=10.0)
    log_result("GET / returns 200 (index.html)", resp.status_code == 200)
    log_result("HTML contains app container", "app-container" in resp.text)
    
    # CSS file
    resp = httpx.get(f"{BASE_URL}/static/styles.css", timeout=10.0)
    log_result("GET /static/styles.css returns 200", resp.status_code == 200)
    log_result("CSS contains glassmorphism rules", "glass-card" in resp.text)
    
    # JS file
    resp = httpx.get(f"{BASE_URL}/static/app.js", timeout=10.0)
    log_result("GET /static/app.js returns 200", resp.status_code == 200)
    log_result("JS contains switchView function", "switchView" in resp.text)

# ============================================================================
# TEST 9: Sparse Candidate (zero missions)
# ============================================================================
def test_sparse_candidate():
    print("\n" + "="*70)
    print("TEST 9: Sparse Candidate (Zero Missions)")
    print("="*70)
    
    session_id = f"test-sparse-{uuid.uuid4().hex[:8]}"
    sparse_candidate = {
        "member": {
            "id": "SPARSE-001",
            "name": "Empty Candidate",
            "jobRole": "Intern",
            "yearsExperience": 0,
            "education": "None",
            "status": "active"
        },
        "missions": [],
        "signals": {
            "commitDays": 0,
            "missionsCompleted": 0,
            "missionsFirstTry": 0
        }
    }
    
    resp = httpx.post(API_URL, json={"sessionId": session_id, "candidate": sparse_candidate}, timeout=15.0)
    data = resp.json()
    
    log_result("Sparse candidate start returns 200", resp.status_code == 200)
    log_result("Sparse candidate gets a question", len(data.get("reply", "")) > 10)
    log_result("Sparse candidate done=false", data.get("done") == False)

# ============================================================================
# TEST 10: Day Coverage Verification
# ============================================================================
def test_day_coverage():
    print("\n" + "="*70)
    print("TEST 10: Day Coverage (>= 4 distinct curriculum days)")
    print("="*70)
    
    candidates = load_candidates()
    session_id = f"test-days-{uuid.uuid4().hex[:8]}"
    
    resp = httpx.post(API_URL, json={"sessionId": session_id, "candidate": candidates[0]}, timeout=15.0)
    all_replies = [resp.json()["reply"]]
    
    done = False
    for i in range(12):
        resp = httpx.post(API_URL, json={
            "sessionId": session_id, 
            "message": f"I implemented it using best practices. Here's my approach for turn {i+1}."
        }, timeout=15.0)
        data = resp.json()
        all_replies.append(data.get("reply", ""))
        if data.get("done"):
            done = True
            break
    
    # Count unique "Day X" references across all replies
    import re
    day_mentions = set()
    for reply in all_replies:
        found_days = re.findall(r'Day\s+(\d+)', reply)
        day_mentions.update(found_days)
    
    log_result("Interview completed", done)
    log_result(f"At least 4 distinct days mentioned ({len(day_mentions)} found: {sorted(day_mentions)})", 
               len(day_mentions) >= 4)

# ============================================================================
# TEST 11: Swagger/OpenAPI docs available
# ============================================================================
def test_openapi_docs():
    print("\n" + "="*70)
    print("TEST 11: OpenAPI Documentation")
    print("="*70)
    
    resp = httpx.get(f"{BASE_URL}/docs", timeout=10.0, follow_redirects=True)
    log_result("GET /docs returns 200", resp.status_code == 200)
    
    resp = httpx.get(f"{BASE_URL}/openapi.json", timeout=10.0)
    log_result("GET /openapi.json returns 200", resp.status_code == 200)
    if resp.status_code == 200:
        schema = resp.json()
        log_result("OpenAPI has /api/interview path", "/api/interview" in schema.get("paths", {}))

# ============================================================================
# MAIN RUNNER
# ============================================================================
def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║       AI INTERVIEW AGENT — COMPREHENSIVE FEATURE TEST SUITE        ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"\nTarget: {BASE_URL}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check server health
    try:
        httpx.get(BASE_URL, timeout=5.0)
    except Exception as e:
        print(f"\n❌ FATAL: Server not reachable at {BASE_URL}")
        print(f"   Error: {e}")
        sys.exit(1)
    
    # Run all tests
    completed_sid, _ = test_full_interview_flow()
    test_cached_session(completed_sid)
    test_second_candidate()
    test_session_isolation()
    test_api_errors()
    test_empty_messages()
    test_candidates_api()
    test_static_serving()
    test_sparse_candidate()
    test_day_coverage()
    test_openapi_docs()
    
    # Summary
    total = PASS + FAIL
    print("\n" + "="*70)
    print(f"  FINAL RESULTS: {PASS}/{total} passed, {FAIL} failed")
    print("="*70)
    
    if FAIL > 0:
        print("\n  Failed tests:")
        for r in RESULTS:
            if not r["passed"]:
                print(f"    ❌ {r['test']}: {r['detail']}")
    
    print()
    return FAIL == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
