# AI Technical Interviewer Agent

A production-style FastAPI backend service and glassmorphic single-page web UI built for technical hackathon evaluations. The agent simulates multi-turn, adaptive technical interviews probing candidates on their Boot Camp learning journey, adjusting questions on the fly based on completed milestones, skipped days, and attempts.

---

## 🏗️ System Architecture

The following diagram illustrates the lifecycle of a technical interview session, mapping candidate focus calculations, API loops, history summarization, and final evaluators.

```mermaid
graph TD
    A[Start Request: POST /api/interview] --> B[Retrieve Curriculum & Candidate Progress]
    B --> C[Compute Focus Map: loader.py]
    C --> D[Initialize Session State SESSIONS]
    D --> E[Generate System Prompt & Adapt Difficulty]
    E --> F[Ask Initial Question on Day 29 welcome]
    F --> G[Conversation Loop]
    G --> H[POST /api/interview message]
    H --> I{Check move_to_next?}
    I -- Yes --> J[Increment Day Focus & Reset Day Counter]
    I -- No --> K[Remain on Current Day]
    J & K --> L[Append User Message & Summarize History if >= 8 msgs]
    L --> M{Check count >= 8 & days >= 4?}
    M -- Yes --> N[Generate Structured Final Feedback JSON]
    M -- No --> O[Call OpenAI / Simulation Fallback]
    O --> P[Strip MOVE_ON and Set move_to_next if needed]
    P --> Q[Return Response to Frontend]
    Q --> G
    N --> R[Cache Session & Return done: true]
```

---

## 🛠️ Configuration Settings

The application reads configurations from environment variables or a local `.env` file. You can swap the completions engine to target OpenAI, DeepSeek, or any local OpenAI-compatible endpoint (like Ollama or LM Studio) with zero code modifications.

| Variable Name | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `OPENAI_API_KEY` | **Yes** | — | API credentials for the LLM completions and evaluator. |
| `OPENAI_BASE_URL` | *No* | Standard OpenAI | URL endpoint targeting compatible providers (e.g. DeepSeek / local Ollama). |
| `OPENAI_MODEL_NAME` | *No* | `gpt-4o-mini` | Model identifier to query for questions and final evaluations. |

---

## 🚀 Getting Started

### 1. Installation
Ensure Python 3.8+ is installed on your local system:

```bash
# Clone and enter directory
cd ai-interviewer-agent

# Set up and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install pinned dependencies
pip install -r requirements.txt
```

### 2. Configure Environment variables
Create a `.env` file matching the template:
```bash
cp .env.example .env
```
Fill in your API credentials:
```ini
OPENAI_API_KEY=your_actual_api_key_here
# OPENAI_BASE_URL=https://api.deepseek.com/v1
# OPENAI_MODEL_NAME=deepseek-chat
```

### 3. Running the Server
Start the Uvicorn dev server:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Frontend User Interface**: Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your web browser.
- **Interactive Swagger Documentation**: Browse [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 4. Running the validation suite
Execute the unit and integration tests:
```bash
# Run pytest suite
python -m pytest

# Run compliance contract test report
python scratch/run_compliance_report.py
```

---

## 📡 Developer API curls Sequence

You can test the complete, multi-turn contract sequence using these cURL commands:

### 1. Initialize Interview (Start Turn)
```bash
curl -X POST "http://127.0.0.1:8000/api/interview" \
     -H "Content-Type: application/json" \
     -d '{
       "sessionId": "curl-test-session-99",
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
     }'
```

### 2. Submit Answer (Conversation Turn)
```bash
curl -X POST "http://127.0.0.1:8000/api/interview" \
     -H "Content-Type: application/json" \
     -d '{
       "sessionId": "curl-test-session-99",
       "message": "I skipped Day 29 monitoring because I ran out of time, but I understand prometheus metrics."
     }'
```

### 3. Check Cached Completed Feedback
Once the interview is concluded (`done: true`), subsequent calls return the cached evaluation directly:
```bash
curl -X POST "http://127.0.0.1:8000/api/interview" \
     -H "Content-Type: application/json" \
     -d '{
       "sessionId": "curl-test-session-99",
       "message": "Hello, is it completed?"
     }'
```
