import json
import httpx

def main():
    print("==========================================================")
    print("RUNNING PROGRAMMATIC MULTI-TURN COMPLIANCE SIMULATION")
    print("==========================================================\n")
    
    # 1. Load Sarah Johnson profile
    with open("candidates.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    sarah = data["candidates"][0] # Sarah Johnson
    
    session_id = "simulation-test-session-123"
    api_url = "http://127.0.0.1:8000/api/interview"
    
    # Answers list to send on each turn
    candidate_answers = [
        # Answer to Turn 1 (Day 29 Observability - initial question)
        "I was behind schedule on Day 29 because I was debugging pipeline failures, so I skipped setting up Prometheus.",
        
        # Answer to Turn 2 (Day 29 Observability - follow-up question)
        "Logs are discrete text events, metrics are numeric counts/gauges, and traces track a single request path across microservices.",
        
        # Answer to Turn 3 (Day 1 Pipelines - initial question)
        "I configured a Github Actions YAML file that runs unit tests on push and builds a Docker container for the service.",
        
        # Answer to Turn 4 (Day 1 Pipelines - follow-up question)
        "The requirements file pins library versions. In production, we pin exact version numbers to avoid breaking changes.",
        
        # Answer to Turn 5 (Day 14 RAG - initial question)
        "RAG retrieves relevant database chunks first and feeds them into the LLM context prompt to reduce model hallucinations.",
        
        # Answer to Turn 6 (Day 14 RAG - follow-up question)
        "I would add system prompt instructions telling the LLM to prioritize the latest, verified chunk or declare if facts conflict.",
        
        # Answer to Turn 7 (Day 7 Embeddings - initial question)
        "I chose PCA to visualize the 768-dimension vectors in 2D space because PCA is linear and preserves global distance.",
        
        # Answer to Turn 8 (Day 7 Embeddings - follow-up question)
        "I would batch document chunks and use asynchronous request pools with retries to stay under OpenAI rate limits."
    ]
    
    # 1. POST START TURN
    print(f"--> [Turn 1] Initializing interview session: {session_id}")
    start_payload = {
        "sessionId": session_id,
        "candidate": sarah
    }
    
    try:
        response = httpx.post(api_url, json=start_payload, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        print(f"   [Interviewer]: {data['reply']}")
        assert data["done"] is False, "Start turn should not be done"
    except Exception as e:
        print(f"Error during Start Turn: {e}")
        return

    # 2. LOOP CONVERSATION TURNS
    for turn_idx, answer in enumerate(candidate_answers):
        turn_num = turn_idx + 1
        print(f"\n--> [Candidate response to Turn {turn_num}]:\n   \"{answer}\"")
        
        turn_payload = {
            "sessionId": session_id,
            "message": answer
        }
        
        try:
            response = httpx.post(api_url, json=turn_payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            if turn_num < 8:
                print(f"--> [Turn {turn_num + 1}] Interviewer Question:\n   [Interviewer]: {data['reply']}")
                assert data["done"] is False, f"Turn {turn_num} should not set done=True"
            else:
                print(f"\n--> [Final Turn] Conclusion:")
                print(f"   [Interviewer]: {data['reply']}")
                assert data["done"] is True, "Final turn must set done=True"
                print("\n==========================================================")
                print("FINAL FEEDBACK STRUCTURE")
                print("==========================================================")
                print(json.dumps(data["feedback"], indent=2))
        except Exception as e:
            print(f"Error during Turn {turn_num}: {e}")
            return

if __name__ == "__main__":
    main()
