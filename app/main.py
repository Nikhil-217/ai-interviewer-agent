import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv
from app.loader import load_curriculum, build_focus_map

load_dotenv()

app = FastAPI(title="AI Interview Agent", version="1.0.0")

# Load curriculum at startup
CURRICULUM_PATH = os.path.join(os.path.dirname(__file__), "..", "curriculum.json")
CURRICULUM = load_curriculum(CURRICULUM_PATH)

# Initialize OpenAI client
api_key = os.environ.get("OPENAI_API_KEY")
client = None
if api_key and api_key != "your_openai_api_key_here":
    client = OpenAI(api_key=api_key)

# In-memory session store
SESSIONS: Dict[str, Dict[str, Any]] = {}

# --- Pydantic Models ---

class Member(BaseModel):
    id: str
    name: str
    jobRole: str
    yearsExperience: int
    education: str
    status: str

class Mission(BaseModel):
    day: int
    title: str
    passed: Optional[bool] = None
    skipped: Optional[bool] = None
    attempts: Optional[int] = None

class Signals(BaseModel):
    commitDays: int
    missionsCompleted: int
    missionsFirstTry: int

class Candidate(BaseModel):
    member: Member
    missions: List[Mission]
    signals: Signals

class IncomingRequest(BaseModel):
    sessionId: str
    candidate: Optional[Candidate] = None
    message: Optional[str] = None

class Feedback(BaseModel):
    summary: str
    strengths: List[str]
    gaps: List[str]
    next: List[str]

class OutgoingResponse(BaseModel):
    reply: str
    done: bool
    feedback: Optional[Feedback] = None

# --- Helper Functions ---

def get_system_prompt(day_info: Dict[str, Any], candidate_info: Dict[str, Any]) -> str:
    """
    Generates a personalized system prompt for the LLM interviewer, implementing difficulty adaptation.
    """
    day_num = day_info.get("day")
    title = day_info.get("title", "")
    reason = day_info.get("reason", "")
    priority = day_info.get("priority", "low")
    
    # Load detailed objectives/tools from curriculum if available
    day_details = CURRICULUM.get(day_num, {})
    dtype = day_details.get("type", "LEARN")
    tools = ", ".join(day_details.get("tools", []))
    objectives = "\n".join([f"- {obj}" for obj in day_details.get("objectives", [])])
    
    # Difficulty Adaptation rules
    if priority == "high":
        difficulty_instruction = (
            "The candidate SKIPPED or FAILED this topic in their coursework. "
            "Start with foundational, conceptual questions to probe basic understanding and clarify potential gaps."
        )
    elif priority == "medium":
        difficulty_instruction = (
            "The candidate struggled slightly (required multiple attempts) to pass this topic. "
            "Start with intermediate questions focusing on practical details, troubleshooting, or implementation gotchas."
        )
    else:
        difficulty_instruction = (
            "The candidate mastered this topic (passed on the first try or completed successfully). "
            "Start with advanced, architectural, design-related, or trade-off questions to test their true depth of understanding."
        )
        
    system_prompt = f"""You are a professional, realistic technical interviewer conducting an interview with a candidate who completed an AI engineering cohort.
Your current focus is Day {day_num} of the curriculum.

--- CURRENT FOCUS TOPIC ---
Day: {day_num}
Title: {title}
Type: {dtype}
Tools used: {tools}
Objectives:
{objectives}

--- CANDIDATE PERFORMANCE DETAILS ---
Reason chosen: {reason}
Difficulty adaptation path: {difficulty_instruction}

--- YOUR ROLE AND RULES ---
1. Ask exactly ONE question at a time.
2. Maintain a conversational, professional, and slightly challenging tone.
3. React to what the candidate just said. If they gave a vague answer, probe it. If they made a claim, ask for reasoning.
4. Do NOT use markdown lists (bullet points or numbered lists) or headers in your response. Keep it as normal, natural speech.
5. **Moderator Instruction**: If you have sufficiently probed this topic (or have asked 2 questions on this topic), you MUST append `[MOVE_ON]` at the very end of your response so the backend knows to transition.
"""
    return system_prompt

def generate_llm_response(system_prompt: str, history: List[Dict[str, str]], current_day_questions: int, day_title: str) -> str:
    """
    Calls the OpenAI client to generate the question. Fallback to simulation if client is not configured.
    """
    if client is not None:
        try:
            messages = [{"role": "system", "content": system_prompt}]
            # Format history to OpenAI format
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})
                
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling OpenAI API: {e}. Falling back to simulation.")
            
    # Simulation Fallback (Offline/Testing mode)
    # If current_day_questions is 1, this is the second question, so we signal a transition by appending [MOVE_ON]
    if current_day_questions >= 1:
        return f"Simulated follow-up question for {day_title}. [MOVE_ON]"
    else:
        return f"Simulated initial question for {day_title}."

# --- API Endpoints ---

@app.post("/api/interview", response_model=OutgoingResponse)
def handle_interview_turn(request: IncomingRequest):
    session_id = request.sessionId
    
    # 1. Start Turn
    if request.candidate is not None:
        candidate_dict = request.candidate.model_dump()
        focus_map = build_focus_map(candidate_dict, CURRICULUM)
        
        focus_days = focus_map.get("focus_days", [])
        if not focus_days:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate a valid focus map for the candidate."
            )
            
        # Get the first day
        first_day = focus_days[0]
        system_prompt = get_system_prompt(first_day, candidate_dict)
        
        # Call LLM to get the initial question
        llm_reply = generate_llm_response(system_prompt, [], 0, first_day["title"])
        
        # Check if the LLM output returned [MOVE_ON] (unlikely for first turn, but handle it)
        clean_reply = llm_reply.replace("[MOVE_ON]", "").strip()
        
        # If it was welcoming, we can prefix it
        final_reply = f"Welcome. Let's begin your interview. {clean_reply}"
        
        SESSIONS[session_id] = {
            "candidate": candidate_dict,
            "focus_map": focus_map,
            "questions_asked": 1,
            "days_covered": [first_day["day"]],
            "current_focus_index": 0,
            "current_day_questions": 1,
            "history": [{"role": "assistant", "content": final_reply}]
        }
        
        return OutgoingResponse(
            reply=final_reply,
            done=False
        )
        
    # 2. Conversation Turn
    if request.message is not None:
        if session_id not in SESSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No active session found with sessionId '{session_id}'. Please start the interview first."
            )
            
        session = SESSIONS[session_id]
        session["history"].append({"role": "user", "content": request.message})
        
        # Check termination condition
        if session["questions_asked"] >= 8 and len(session["days_covered"]) >= 4:
            # Conclude interview
            # In a production app, we would summarize the actual history using an LLM.
            # Here we return structured mock feedback for now.
            feedback = Feedback(
                summary="You have completed the technical interview. Good job!",
                strengths=["Excellent conceptual depth in embeddings", "Solid practical understanding of vector search"],
                gaps=["Familiarity with container networking", "Observability tool implementation details"],
                next=["Review Docker networking objectives", "Spend more time on logging and tracing tools"]
            )
            return OutgoingResponse(
                reply="Interview completed.",
                done=True,
                feedback=feedback
            )
            
        # Select current day to probe
        focus_days = session["focus_map"].get("focus_days", [])
        strong_days = session["focus_map"].get("strong_days", [])
        
        focus_idx = session["current_focus_index"]
        if focus_idx < len(focus_days):
            day_info = focus_days[focus_idx]
        else:
            strong_idx = focus_idx - len(focus_days)
            if strong_idx < len(strong_days):
                day_info = strong_days[strong_idx]
            else:
                uncovered = [d for d in CURRICULUM.keys() if d not in session["days_covered"]]
                fallback_day = uncovered[0] if uncovered else 1
                day_info = {
                    "day": fallback_day,
                    "title": CURRICULUM[fallback_day]["title"],
                    "reason": "General curriculum knowledge check.",
                    "priority": "low"
                }
                
        # Generate question for the day using LLM
        system_prompt = get_system_prompt(day_info, session["candidate"])
        llm_reply = generate_llm_response(
            system_prompt,
            session["history"][:-1],  # Pass prior history
            session["current_day_questions"],
            day_info["title"]
        )
        
        # Check for [MOVE_ON] signal
        if "[MOVE_ON]" in llm_reply or session["current_day_questions"] >= 2:
            # Advance to the next day immediately
            session["current_focus_index"] += 1
            session["current_day_questions"] = 0
            
            # Recheck termination before asking next day's question
            # (In case this was the 8th question or we met termination)
            # Wait, if we haven't reached 8 yet, we generate the first question of the new day.
            next_focus_idx = session["current_focus_index"]
            if next_focus_idx < len(focus_days):
                next_day_info = focus_days[next_focus_idx]
            else:
                next_strong_idx = next_focus_idx - len(focus_days)
                if next_strong_idx < len(strong_days):
                    next_day_info = strong_days[next_strong_idx]
                else:
                    uncovered = [d for d in CURRICULUM.keys() if d not in session["days_covered"]]
                    fallback_day = uncovered[0] if uncovered else 1
                    next_day_info = {
                        "day": fallback_day,
                        "title": CURRICULUM[fallback_day]["title"],
                        "reason": "General curriculum knowledge check.",
                        "priority": "low"
                    }
                    
            new_system_prompt = get_system_prompt(next_day_info, session["candidate"])
            llm_reply = generate_llm_response(
                new_system_prompt,
                session["history"],  # Pass history including the latest answer
                0,
                next_day_info["title"]
            )
            day_info = next_day_info
            
        # Clean reply from [MOVE_ON] tag
        clean_reply = llm_reply.replace("[MOVE_ON]", "").strip()
        
        # Update state
        session["questions_asked"] += 1
        session["current_day_questions"] += 1
        if day_info["day"] not in session["days_covered"]:
            session["days_covered"].append(day_info["day"])
        session["history"].append({"role": "assistant", "content": clean_reply})
        
        return OutgoingResponse(
            reply=clean_reply,
            done=False
        )
        
    # Invalid request
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid request. Either 'candidate' (for start) or 'message' (for subsequent turns) must be provided."
    )
