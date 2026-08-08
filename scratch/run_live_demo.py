import json
import httpx

def main():
    print("==========================================================")
    print("RUNNING LIVE TECHNICAL INTERVIEW DEMO WITH OPENAI API")
    print("==========================================================\n")
    
    # 1. Load Candidate Sarah Johnson
    with open("candidates.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    sarah = data["candidates"][0] # Sarah Johnson
    
    session_id = "live-demo-session-1"
    
    # Start Turn request
    start_payload = {
        "sessionId": session_id,
        "candidate": sarah
    }
    
    print("--> Posting Start Turn for Sarah Johnson...")
    try:
        response = httpx.post("http://127.0.0.1:8000/api/interview", json=start_payload, timeout=20.0)
        response.raise_for_status()
        data = response.json()
        print(f"\n[Interviewer Reply]:\n{data['reply']}\n")
    except Exception as e:
        print(f"Error during Start Turn request: {e}")
        return
        
    # Send Conversation Turn
    answer = "I struggled a lot with Prometheus metrics and structured logging config because I ran out of time on Day 29, so I had to skip it."
    print(f"--> Posting Candidate Answer:\n\"{answer}\"")
    
    turn_payload = {
        "sessionId": session_id,
        "message": answer
    }
    
    try:
        response = httpx.post("http://127.0.0.1:8000/api/interview", json=turn_payload, timeout=20.0)
        response.raise_for_status()
        data = response.json()
        print(f"\n[Interviewer Follow-up]:\n{data['reply']}\n")
    except Exception as e:
        print(f"Error during Conversation Turn request: {e}")
        return

if __name__ == "__main__":
    main()
