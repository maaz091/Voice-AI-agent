# Voice AI Agent — Patient Registration System

An enterprise-ready voice-based AI agent accessible via a real U.S. telephone number that collects patient demographic information through natural conversation, persists data to a cloud PostgreSQL database, and exposes a RESTful API.

---

## Submission Details

- **GitHub Repository**: [https://github.com/maaz091/Voice-AI-agent](https://github.com/maaz091/Voice-AI-agent)
- **Live Phone Number**: `+1 (434) 454-3104` (Call from any US/international phone)
- **Live REST API Base URL**: [https://voice-ai-agent-10sa.onrender.com](https://voice-ai-agent-10sa.onrender.com)
- **Interactive Swagger UI**: [https://voice-ai-agent-10sa.onrender.com/docs](https://voice-ai-agent-10sa.onrender.com/docs)
- **Interactive ReDoc**: [https://voice-ai-agent-10sa.onrender.com/redoc](https://voice-ai-agent-10sa.onrender.com/redoc)

---

## Architecture Overview

```
Caller (Phone) ──► Vapi.ai (Telephony & Orchestration)
                       │
                       ├─► STT: Soniox STT RT v5
                       ├─► LLM: OpenAI GPT-4.1 (Prompt & Tools)
                       └─► TTS: ElevenLabs Eleven Turbo v2.5 (Sarah)
                              │
                              ▼ REST API Calls (Tools)
                 FastAPI Backend Service (Docker on Render)
                              │
                              ▼ SQLModel / SQLAlchemy Engine
                 Cloud PostgreSQL Database (Neon Serverless)
```

| Layer | Technology | Rationale & Justification |
|---|---|---|
| **Telephony & Agent Orchestration** | Vapi.ai | Production-grade WebRTC/SIP bridge, ultra-low latency streaming, function calling integration. |
| **Voice Synthesis (TTS)** | ElevenLabs `Eleven Turbo v2.5` (`Sarah`) | Natural prosody, realistic pauses, and human-like clinical tone. |
| **Speech-to-Text (STT)** | Soniox STT RT v5 | Fast real-time streaming recognition (1.8% WER, ~410ms latency) for alphanumeric characters and spellings. |
| **Reasoning Engine (LLM)** | OpenAI GPT-4.1 | High conversational intelligence, robust tool calling, fast ~690ms latency. |
| **Backend API** | FastAPI + SQLModel | High-performance asynchronous REST framework with strict Pydantic envelope validation. |
| **Database** | Neon PostgreSQL (Serverless) | Cloud-hosted, persistent across redeploys, connection pooling with resilient auto-reconnect. |
| **Hosting & CI/CD** | Render (Docker Runtime) | Automated container builds and deployments from GitHub repository. |

---

## Key Assessment Requirements & Implementation Highlights

### 1. Strict Envelope Responses
Every single API endpoint returns the uniform JSON envelope:
```json
{
  "data": <object | array | null>,
  "error": <string | null>
}
```
Custom exception handlers in `app/main.py` override FastAPI's default 422, 404, and 500 error formats to guarantee strict compliance.

### 2. Patient Data Model & Voice Tolerant Validation
- **`date_of_birth`**: Stored as a true SQL `Date` column and serialized as `MM/DD/YYYY` in all outputs. The validator accepts `MM/DD/YYYY`, `YYYY-MM-DD`, and natural voice representations.
- **`sex`**: Strictly validated against `SexEnum` (`"Male"`, `"Female"`, `"Other"`, `"Decline to Answer"`).
- **`phone_number`**: Auto-cleans formatted speech (e.g. `(555) 123-4567` or `555-123-4567`) to exact 10 digits.
- **`state`**: Maps full state names (e.g. "Texas", "California") to 2-letter uppercase codes (`TX`, `CA`).
- **`deleted_at`**: Soft-delete pattern; soft-deleted records are automatically excluded from list and lookup queries.

### 3. Conversational Capabilities & Edge Cases
1. **Returning Patient Duplicate Detection**: Prompt initiates phone lookup first. If the caller exists, it welcomes them by first name and enters partial update mode.
2. **Partial Updates**: Updates only the requested field (e.g. `"update my city to Dallas"`) without nullifying other fields.
3. **Conversational Self-Correction**: Caller can say "actually my last name is..." or "start over" at any point.
4. **Invalid Input Handling**: Checks for invalid or future birth dates, polite re-prompting.
5. **Confirmation Step**: Reads back all demographic data before calling the creation tool.

---

## Project Structure

```
Voice-AI-agent/
├── app/
│   ├── __init__.py           # Package marker
│   ├── main.py               # FastAPI initialization, CORS, envelope exception handlers
│   ├── models.py             # SQLModel table, schemas, enums, voice validators
│   ├── database.py           # Engine creation (Neon PostgreSQL with SQLite fallback)
│   ├── routes.py             # 5 REST endpoints + health check + stdout logging
│   └── seed.py               # Automatic seeding of initial records on startup
├── test_suite.py             # 13 comprehensive in-process tests (TestClient)
├── VOICE_AGENT_SETUP.md      # Detailed system prompt & Vapi tool schema configurations
├── Dockerfile                # Production Docker container definition
├── render.yaml               # Render Infrastructure-as-Code deploy spec
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
└── README.md                 # Complete documentation
```

---

## Local Development & Testing

### 1. Installation
```bash
# Clone repository
git clone https://github.com/maaz091/Voice-AI-agent.git
cd Voice-AI-agent

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Server Locally
```bash
# Starts with SQLite fallback if DATABASE_URL is unset
python -m uvicorn app.main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` to test via Swagger UI.

### 3. Running the Automated Test Suite
```bash
python test_suite.py
```
This runs 13 automated tests covering:
- Health check (200)
- GET `/patients` (List & filters)
- GET `/patients/{id}` (UUID lookup & 404 envelope)
- POST `/patients` (Creation & 201 envelope)
- PUT `/patients/{id}` (Partial updates)
- DELETE `/patients/{id}` (Soft deletion & exclusion)
- 422 Validation errors (Invalid DOB, invalid name characters, invalid phone length, invalid sex enum)

---

## Testing Guide for Reviewers

### Option A: Test via Live Voice Phone Call
1. Dial **`+1 (434) 454-3104`** from any phone.
2. **Test New Patient Registration**:
   - Provide phone number: `5551234567` (or your own number)
   - Provide Name, DOB, Sex, and Address.
   - Confirm details when read back.
   - Verify creation immediately on `https://voice-ai-agent-10sa.onrender.com/patients`.
3. **Test Returning Patient & Update**:
   - Call back with the same phone number.
   - The assistant greets you: *"It looks like we already have a record for [Name]..."*
   - Say: *"Please update my city to Dallas"*.
   - Verify update in the live database.

### Option B: Test via Live REST API
- **List Patients**:
  ```bash
  curl -s https://voice-ai-agent-10sa.onrender.com/patients
  ```
- **Lookup by Phone**:
  ```bash
  curl -s "https://voice-ai-agent-10sa.onrender.com/patients?phone_number=5550100000"
  ```
- **Create Patient**:
  ```bash
  curl -X POST https://voice-ai-agent-10sa.onrender.com/patients \
    -H "Content-Type: application/json" \
    -d '{
      "first_name": "Marcus",
      "last_name": "Aurelius",
      "date_of_birth": "04/26/1980",
      "sex": "Male",
      "phone_number": "5559998888",
      "address_line_1": "1 Palatine Hill",
      "city": "Rome",
      "state": "NY",
      "zip_code": "10001"
    }'
  ```

---

## Design Trade-offs & Known Limitations

1. **Authentication Scope**: Per the assessment instructions, API endpoints are publicly accessible to allow direct reviewer testing and Vapi webhook calls. In a production deployment, API keys or OAuth2 JWT tokens would guard all write endpoints.
2. **Cold Starts on Render Free Tier**: The web service runs on Render's container runtime. If inactive, the service may spin down (taking ~30s on initial cold request). Neon PostgreSQL database persistence remains unaffected.
3. **CORS Configuration**: Wildcard CORS (`*`) is enabled for seamless cross-origin inspection and webhook integration.
4. **HIPAA Compliance**: As noted in the assignment requirements, this system is a proof-of-concept demonstration and does not contain Protected Health Information (PHI). Production rollout would require a HIPAA-compliant BAA with cloud providers, encrypted storage-at-rest, and audit logging.

---

## Prompt & LLM System Message

The complete prompt is documented in [`VOICE_AGENT_SETUP.md`](VOICE_AGENT_SETUP.md) and configured in the Vapi assistant. Key prompt techniques include:
- Step-by-step sequential intake preventing cognitive overload.
- Strict phone formatting rules (10 digits without punctuation).
- Explicit enum mappings and date format normalization.
- Read-back confirmation before committing database writes.
- Conversational recovery pathways ("start over", field corrections, polite repetition).
