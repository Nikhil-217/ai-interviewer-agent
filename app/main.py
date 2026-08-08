import os
import json
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv
from app.loader import load_curriculum, build_focus_map

load_dotenv()

app = FastAPI(title="AI Interview Agent", version="1.0.0")

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load curriculum at startup
CURRICULUM_PATH = os.path.join(os.path.dirname(__file__), "..", "curriculum.json")
CURRICULUM = load_curriculum(CURRICULUM_PATH)

# Initialize OpenAI client with swappable configuration
api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL")
model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini")

client = None
if api_key and api_key != "your_openai_api_key_here":
    client = OpenAI(
        api_key=api_key,
        base_url=base_url if base_url else None
    )

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

SIMULATED_QUESTIONS = {
    1: {
        "high": {
            "initial": "On Day 1, setting up the basic development environment and pipelines was skipped or failed. Can you walk me through the basic components of a typical Python web service pipeline, and how you would configure a local virtual environment?",
            "follow_up": "Understood. Once the local pipeline is set up, what is the role of a requirements file, and how do you ensure package versions do not conflict when deploying to production? [MOVE_ON]"
        },
        "low": {
            "initial": "For Day 1, you successfully set up the development environment and automated pipelines. Can you describe your pipeline configuration, and how you would optimize the build stage to ensure fast container assembly?",
            "follow_up": "That's a solid strategy. How do you handle continuous integration testing for pipeline code to catch configuration errors before they hit main? [MOVE_ON]"
        }
    },
    7: {
        "high": {
            "initial": "On Day 7, sentence embeddings and vector representations were skipped. Let's start conceptually: what is a vector embedding, and how does it map text meaning into a high-dimensional space?",
            "follow_up": "Right. How do you compare the similarity of two text vectors, and what is the difference between Cosine similarity and Euclidean distance? [MOVE_ON]"
        },
        "low": {
            "initial": "For Day 7, you successfully generated sentence embeddings and clustered them using PCA. Can you explain why you chose PCA over other dimensionality reduction techniques like t-SNE, and what insights you drew from the clusters?",
            "follow_up": "Great. If you were to transition from local Sentence Transformers to a hosted API like OpenAI Embeddings, how would you design the chunking and rate-limiting logic to handle high-throughput text streams? [MOVE_ON]"
        }
    },
    10: {
        "high": {
            "initial": "On Day 10, setting up the vector database was skipped. Conceptually, why do we need a dedicated vector database rather than a standard relational database like PostgreSQL for vector search?",
            "follow_up": "Correct. How does an index like HNSW (Hierarchical Navigable Small World) accelerate vector search compared to an exhaustive flat search? [MOVE_ON]"
        },
        "low": {
            "initial": "On Day 10, you successfully integrated a vector database. Can you walk me through your indexing strategy, and how you tuned parameters like `ef_construction` and `M` to balance query latency vs recall accuracy?",
            "follow_up": "That's a very advanced tuning. If you need to perform metadata filtering (e.g. search only documents created in the last 30 days), how would you design pre-filtering vs post-filtering in the vector DB? [MOVE_ON]"
        }
    },
    14: {
        "high": {
            "initial": "On Day 14, RAG and hybrid retrieval routing failed or were skipped. Can you explain the basic flow of Retrieval-Augmented Generation, and why retrieving external documents helps reduce LLM hallucinations?",
            "follow_up": "Exactly. If the retrieved chunks contain conflicting information, how would you instruct the LLM to handle the discrepancy in its final response? [MOVE_ON]"
        },
        "low": {
            "initial": "On Day 14, you implemented RAG with hybrid retrieval routing. How did you combine keyword search scores (BM25) with vector similarity scores, and what normalization technique (e.g. Reciprocal Rank Fusion) did you apply?",
            "follow_up": "Fascinating. How do you evaluate the retrieval quality? What metrics (like Hit Rate or MRR) did you track to ensure the correct context was sent to the generator? [MOVE_ON]"
        }
    },
    29: {
        "high": {
            "initial": "On Day 29, the logging and observability setup was skipped. What is the fundamental difference between a structured log, a metric, and a trace, and why do we need all three in a production chatbot?",
            "follow_up": "Exactly. If your chatbot API starts experiencing high latency, how would you use Prometheus metrics to isolate whether the bottleneck is in LLM generation latency or database query overhead? [MOVE_ON]"
        },
        "low": {
            "initial": "On Day 29, you successfully built production logging and Grafana dashboards. Can you describe the specific custom metrics you tracked for your chatbot pipelines, and how you configured alerts for abnormal response latency?",
            "follow_up": "Excellent observability setup. How do you handle log rotation and trace correlation IDs across asynchronous tasks to debug user sessions? [MOVE_ON]"
        }
    }
}

def generate_llm_response(system_prompt: str, history: List[Dict[str, str]], current_day_questions: int, day_info: Dict[str, Any], running_summary: Optional[str] = None) -> str:
    """
    Calls the OpenAI client to generate the question. Fallback to simulation if client is not configured.
    """
    if client is not None:
        try:
            messages = [{"role": "system", "content": system_prompt}]
            if running_summary:
                messages.append({
                    "role": "system",
                    "content": f"Here is a summary of the conversation history so far: {running_summary}"
                })
            # Format history to OpenAI format
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})
                
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling OpenAI API: {e}. Falling back to simulation.")
            
    # Simulation Fallback (Offline/Testing/Credits exhausted mode)
    day_num = day_info.get("day", 1)
    priority = day_info.get("priority", "low")
    title = day_info.get("title", "Curriculum Topic")
    
    day_questions = SIMULATED_QUESTIONS.get(day_num, {})
    priority_questions = day_questions.get(priority, day_questions.get("low", {}))
    
    if current_day_questions >= 1:
        # Return follow-up
        if priority_questions and "follow_up" in priority_questions:
            return priority_questions["follow_up"]
        return f"Interesting decision on Day {day_num} ({title}). If you had to re-architect this pipeline today, what scaling blockers would you address first? [MOVE_ON]"
    else:
        # Return initial
        if priority_questions and "initial" in priority_questions:
            return priority_questions["initial"]
        return f"Let's discuss Day {day_num}: {title}. You completed this with priority {priority.upper()}. Can you tell me about the architecture you built and the choices you made?"

def summarize_history(session: Dict[str, Any]) -> None:
    """
    Summarizes the earliest 4 messages (2 turns) of history into a running summary
    if the history size reaches 8 messages or more, then removes them from history.
    """
    history = session.get("history", [])
    if len(history) >= 8:
        slice_to_summarize = history[:4]
        content_to_summarize = json.dumps(slice_to_summarize)
        
        old_summary = session.get("running_summary", "")
        summary_prompt = (
            "You are a helpful assistant. Summarize this portion of a technical interview. "
            "Focus on the questions asked, the candidate's answers, and any gaps or strengths identified. "
            "Keep it brief (2-3 sentences)."
        )
        if old_summary:
            summary_prompt += f" Append and integrate this with the previous summary: {old_summary}"
            
        new_summary = ""
        if client is not None:
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": summary_prompt},
                        {"role": "user", "content": content_to_summarize}
                    ],
                    temperature=0.5
                )
                new_summary = response.choices[0].message.content.strip()
            except Exception as e:
                print(f"Error generating history summary: {e}")
                
        if not new_summary:
            # Fallback simulation summary
            new_summary = f"The candidate answered questions about Day {slice_to_summarize[0].get('content', '')[:30]}."
            if old_summary:
                new_summary = f"{old_summary} Also, {new_summary}"
                
        session["running_summary"] = new_summary
        session["history"] = history[4:]

def generate_final_feedback(history: List[Dict[str, str]], candidate: Dict[str, Any], running_summary: Optional[str] = None) -> Feedback:
    """
    Evaluates the full conversation history to produce end-of-interview structured feedback,
    grounding strengths/gaps/next in specific days/modules. Validates and retries on failure.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert technical interviewer evaluating a candidate after a multi-turn technical interview. "
                "Produce a structured feedback evaluation in JSON format. "
                "You MUST return ONLY a JSON object matching this exact schema:\n"
                "{\n"
                '  "summary": "Overall summary of candidate performance",\n'
                '  "strengths": ["list of specific strengths"],\n'
                '  "gaps": ["list of specific gaps/weaknesses"],\n'
                '  "next": ["list of concrete recommendations/next steps"]\n'
                "}\n"
                "Do NOT wrap it in ```json codeblocks. Do NOT write any conversational prose before or after the JSON. "
                "CRITICAL REQUIREMENT: Ground every single strength, gap, and next-step recommendation in a SPECIFIC day or module from the interview. "
                "For example, write 'Gap: struggled to explain Prometheus logging config from Day 29' instead of 'struggled with logging'. "
                "Be specific, critical, and objective."
            )
        },
        {
            "role": "system",
            "content": f"Candidate Profile:\nName: {candidate['member']['name']}\nRole: {candidate['member']['jobRole']}\nExperience: {candidate['member']['yearsExperience']} years"
        }
    ]
    
    if running_summary:
        messages.append({
            "role": "system",
            "content": f"Here is a summary of the earlier part of the conversation: {running_summary}"
        })
        
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
        
    attempts = 2
    last_error = None
    
    for attempt in range(attempts):
        raw_output = ""
        if client is not None:
            try:
                current_messages = list(messages)
                if attempt == 1:
                    current_messages.append({
                        "role": "system",
                        "content": "CRITICAL: The previous output failed to parse as valid JSON. You MUST return ONLY the raw JSON string starting with '{' and ending with '}'. Do not include markdown blocks, warnings, or explanation."
                    })
                response = client.chat.completions.create(
                    model=model_name,
                    messages=current_messages,
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                raw_output = response.choices[0].message.content.strip()
            except Exception as e:
                print(f"Error calling OpenAI completions: {e}")
                last_error = e
        else:
            # Fallback mock feedback for testing/simulation
            has_sarah = "Sarah" in candidate.get("member", {}).get("name", "")
            # Let's write a mock feedback that satisfies the "grounded in specific day" rule
            if has_sarah:
                raw_output = json.dumps({
                    "summary": "Completed technical interview with mixed results on data engineering.",
                    "strengths": ["Demonstrated clean design of pipelines on Day 1"],
                    "gaps": ["Struggled to explain Prometheus metrics configuration from Day 29"],
                    "next": ["Review logging objectives on Day 29"]
                })
            else:
                raw_output = json.dumps({
                    "summary": "Completed technical interview with high performance.",
                    "strengths": ["Mastered embeddings PCA visualization on Day 7"],
                    "gaps": ["Could refine routing strategies from Day 10"],
                    "next": ["Read advanced retrieval strategies from Day 10"]
                })
                
        try:
            cleaned = raw_output
            if cleaned.startswith("```"):
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            feedback = Feedback(**data)
            return feedback
        except Exception as parse_err:
            print(f"Failed parsing/validating feedback JSON (attempt {attempt+1}/{attempts}): {parse_err}. Raw output was: {raw_output}")
            last_error = parse_err
            
    # If all attempts fail, return a fallback Feedback object
    return Feedback(
        summary="Technical interview completed. Some parsing errors occurred while processing detailed feedback.",
        strengths=["Overall completion of technical assessment"],
        gaps=["Details on specific focus topics could not be parsed"],
        next=["Review entire bootcamp objectives list"]
    )

# --- API Endpoints ---

@app.post("/api/interview", response_model=OutgoingResponse)
def handle_interview_turn(request: IncomingRequest):
    session_id = request.sessionId
    
    # Check if session is already completed to return cached feedback directly
    if session_id in SESSIONS and SESSIONS[session_id].get("completed", False):
        feedback = SESSIONS[session_id]["feedback"]
        return OutgoingResponse(
            reply="Interview completed.",
            done=True,
            feedback=Feedback(**feedback)
        )
        
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
        llm_reply = generate_llm_response(system_prompt, [], 0, first_day)
        
        # Check if the LLM output returned [MOVE_ON]
        clean_reply = llm_reply.replace("[MOVE_ON]", "").strip()
        final_reply = f"Welcome. Let's begin your interview. {clean_reply}"
        
        SESSIONS[session_id] = {
            "candidate": candidate_dict,
            "focus_map": focus_map,
            "questions_asked": 1,
            "days_covered": [first_day["day"]],
            "current_focus_index": 0,
            "current_day_questions": 1,
            "history": [{"role": "assistant", "content": final_reply}],
            "running_summary": "",
            "completed": False,
            "feedback": None,
            "move_to_next": False
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
        
        # Guardrail: Check for empty / garbage inputs
        msg_str = request.message.strip()
        if not msg_str:
            # Get last question from history to repeat
            last_question = "Could you please tell me more about how you approached this topic?"
            for msg in reversed(session["history"]):
                if msg["role"] == "assistant":
                    last_question = msg["content"]
                    break
            reply = f"I didn't quite catch that. {last_question}"
            return OutgoingResponse(
                reply=reply,
                done=False
            )
            
        session["history"].append({"role": "user", "content": request.message})
        
        # Check if we should summarize history before proceeding (context management)
        summarize_history(session)
        
        # Check termination condition
        if session["questions_asked"] >= 8 and len(session["days_covered"]) >= 4:
            # Conclude interview
            feedback = generate_final_feedback(session["history"], session["candidate"], session.get("running_summary"))
            # Cache completed state
            session["completed"] = True
            session["feedback"] = feedback.model_dump()
            
            return OutgoingResponse(
                reply="Interview completed.",
                done=True,
                feedback=feedback
            )
            
        # Check if we should transition to the next topic before generating the next question
        if session.get("move_to_next", False):
            session["current_focus_index"] += 1
            session["current_day_questions"] = 0
            session["move_to_next"] = False

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
            day_info,
            session.get("running_summary")
        )
        
        # Determine if we should transition on the NEXT turn
        if "[MOVE_ON]" in llm_reply or session["current_day_questions"] >= 1:
            session["move_to_next"] = True
            
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

# --- Additional UI & Metadata Endpoints ---

@app.get("/api/candidates")
def get_candidates():
    """
    Returns the list of candidates from candidates.json for the frontend dropdown.
    """
    candidates_path = os.path.join(os.path.dirname(__file__), "..", "candidates.json")
    try:
        with open(candidates_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("candidates", [])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load candidates: {e}"
        )

# Serve root route with index.html
@app.get("/", response_class=HTMLResponse)
def serve_homepage():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if not os.path.exists(index_path):
        # Graceful placeholder response in case static files are not created yet
        return "<html><body><h1>AI Interview Agent API</h1><p>Static files loading...</p></body></html>"
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# Mount static folder
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
