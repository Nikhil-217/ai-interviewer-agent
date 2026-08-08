# AI Interview Agent

A production-style backend service built for a technical hackathon challenge. This API conducts realistic, multi-turn, adaptive technical interviews with candidates based on their learning history from a 31-day engineering boot camp. 

Instead of static, quiz-like templates, this agent tailors every question and evaluation dynamically to what the candidate completed, skipped, or struggled with, adjusting query difficulty on the fly.

---

## Key Features

1. **Focus Map Scheduler**: Evaluates candidate metrics and boot camp history deterministically to prioritize high-risk gaps (skipped/failed days) and verify masteries.
2. **Orchestrator State Machine**: Manages session progression across curriculum topics, asking exactly 2 questions per day and concluding after covering $\ge 4$ distinct days and $\ge 8$ total questions.
3. **Adaptive LLM Prompts**: Implements difficulty adaptation (conceptual/foundational questions for skipped days; advanced trade-off/design questions for first-try masteries).
4. **Hardened Context & Token Management**: Binds context bloat by dynamically summarizing history turns once history size reaches 8 messages, keeping the memory footprint minimal.
5. **JSON Feedback Grounding**: Produces structured feedback reports validated against Pydantic schemas, with strengths, gaps, and recommendations grounded in specific curriculum days.
6. **Provider Swappability**: Full swappability to target OpenAI, DeepSeek, or local LLMs (like Ollama, LM Studio, or vLLM) with zero code modifications.

---

## Local Setup

### 1. Prerequisites
- Python 3.8 or higher.
- Git (optional).

### 2. Installation
Clone the repository and install the pinned dependencies:

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the configuration template and add your API keys:

```bash
cp .env.example .env
```

Open `.env` and fill in:
```ini
OPENAI_API_KEY=your_real_openai_api_key

# Optional parameters to target alternative providers (e.g. DeepSeek / Ollama)
# OPENAI_BASE_URL=https://api.deepseek.com/v1
# OPENAI_MODEL_NAME=deepseek-chat
```

---

## Running the Application

### 1. Start Server locally
Start the FastAPI development server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API docs will be available at: [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Run with Docker
Alternatively, spin up the server inside a Docker container:

```bash
# Build the container
docker build -t ai-interview-agent .

# Run the container
docker run -p 8000:8000 --env-file .env ai-interview-agent
```

---

## Verification & Testing

Verify system compliance, state machine progression, isolation, and feedback schemas:

```bash
# Run the entire test suite
python -m pytest

# Run compliance contract test report
python scratch/run_compliance_report.py
```

---

## API Contract & Sample Sequence

The agent exposes a single `POST /api/interview` endpoint maintaining session state in-memory.

### 1. Start Turn
Initialize the interview session for a candidate profile.

**Request (`POST /api/interview`)**:
```json
{
  "sessionId": "hackathon-session-abc",
  "candidate": {
    "member": {
      "id": "CAND-001",
      "name": "Sarah Johnson",
      "jobRole": "Senior Data Engineer",
      "yearsExperience": 9,
      "education": "MS Data Science",
      "status": "active"
    },
    "missions": [
      { "day": 1, "title": "Pipeline Setup", "passed": true, "attempts": 1 },
      { "day": 29, "title": "Monitoring & Observability", "skipped": true }
    ],
    "signals": {
      "commitDays": 19,
      "missionsCompleted": 24,
      "missionsFirstTry": 2
    }
  }
}
```

**Response**:
```json
{
  "reply": "Welcome. Let's begin your interview. How would you approach building a pipeline setup on Day 1?",
  "done": false,
  "feedback": null
}
```

### 2. Intermediate Conversation Turn
Provide candidate answers and receive follow-up questions.

**Request (`POST /api/interview`)**:
```json
{
  "sessionId": "hackathon-session-abc",
  "message": "I used GitHub actions and set up Dockerized runners for pipeline deployment."
}
```

**Response**:
```json
{
  "reply": "Let's explore Day 29: Monitoring and Observability. Why was this skipped in your boot camp journey?",
  "done": false,
  "feedback": null
}
```

### 3. Final Turn (Turn 8)
When the session concludes, the API returns the final evaluation feedback.

**Request (`POST /api/interview`)**:
```json
{
  "sessionId": "hackathon-session-abc",
  "message": "We set up Grafana dashboard monitoring to collect metrics."
}
```

**Response**:
```json
{
  "reply": "Interview completed.",
  "done": true,
  "feedback": {
    "summary": "Completed technical interview with mixed results on data engineering.",
    "strengths": ["Demonstrated clean design of pipelines on Day 1"],
    "gaps": ["Struggled to explain Prometheus metrics configuration from Day 29"],
    "next": ["Review logging objectives on Day 29"]
  }
}
```
