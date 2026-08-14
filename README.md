# Voice AI Agent — Patient Registration System

A voice-based AI agent accessible via a real phone number that collects standard U.S. patient demographic information through natural conversation, persists that data to a PostgreSQL database, and exposes it through a RESTful API.

## Architecture

```
Phone Call (Caller) → Vapi.ai (Voice AI + LLM) → FastAPI Backend → Neon PostgreSQL
                                                        ↑
                                                  REST API Client
```

| Layer | Technology | Justification |
|---|---|---|
| **Telephony + Voice AI** | Vapi.ai | Abstracts STT/TTS/telephony complexity. Free trial with phone number included. |
| **LLM** | GPT-4o-mini (via Vapi) | Best quality-to-cost ratio for conversational tasks. |
| **Backend** | Python + FastAPI | Async-capable, auto-generated OpenAPI docs, built-in Pydantic validation. |
| **Database** | PostgreSQL (Neon) | Cloud-hosted, persistent across deploys, free tier. SQLModel makes the ORM code identical to SQLite. |
| **Hosting** | Render.com | Free tier, Docker support, 1-click deploy from GitHub. |

## Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- pip

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd voice-ai-agent

# Install dependencies
pip install -r requirements.txt

# (Optional) Set up environment variables for Neon PostgreSQL
cp .env.example .env
# Edit .env with your Neon DATABASE_URL

# Run the server (uses SQLite by default if no DATABASE_URL is set)
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`. Two seed patient records are automatically inserted on first run.

### API Documentation
FastAPI auto-generates interactive API docs:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes (prod) | `sqlite:///./patients.db` | PostgreSQL connection string from Neon |
| `PORT` | No | `8000` | Server port (Render sets this automatically) |

## API Endpoints

All responses use the strict envelope format:
```json
{ "data": <payload or null>, "error": <string or null> }
```

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `GET` | `/` | 200 | Health check |
| `GET` | `/patients` | 200 | List all non-deleted patients. Filters: `?last_name=`, `?date_of_birth=`, `?phone_number=` |
| `GET` | `/patients/{id}` | 200/404 | Get patient by UUID |
| `POST` | `/patients` | 201 | Create new patient |
| `PUT` | `/patients/{id}` | 200/404 | Partial update |
| `DELETE` | `/patients/{id}` | 200/404 | Soft-delete (sets `deleted_at`) |

### Example: Create a Patient

```bash
curl -X POST http://localhost:8000/patients \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Alice",
    "last_name": "Brown",
    "date_of_birth": "01/15/1992",
    "sex": "Female",
    "phone_number": "5551234567",
    "address_line_1": "789 Pine St",
    "city": "Chicago",
    "state": "IL",
    "zip_code": "60601"
  }'
```

### Example: Validation Error Response (422)

```json
{
  "data": null,
  "error": "first_name: Value error, first_name must be 1-50 characters and contain only letters, hyphens, and apostrophes"
}
```

## Patient Data Model

| Field | Type | Validation | Required |
|---|---|---|---|
| `patient_id` | UUID | Auto-generated | Auto |
| `first_name` | String | 1-50 chars, alphabetic + hyphens/apostrophes | Yes |
| `last_name` | String | 1-50 chars, alphabetic + hyphens/apostrophes | Yes |
| `date_of_birth` | Date | MM/DD/YYYY format, not in future | Yes |
| `sex` | Enum | Male, Female, Other, Decline to Answer | Yes |
| `phone_number` | String | Exactly 10 digits | Yes |
| `email` | String | Valid email format | No |
| `address_line_1` | String | Street address | Yes |
| `address_line_2` | String | Apt/Suite/Unit | No |
| `city` | String | 1-100 characters | Yes |
| `state` | String | 2-letter US state abbreviation | Yes |
| `zip_code` | String | 5-digit or ZIP+4 format | Yes |
| `insurance_provider` | String | Insurance company name | No |
| `insurance_member_id` | String | Member/subscriber ID | No |
| `preferred_language` | String | Default: "English" | No |
| `emergency_contact_name` | String | Full name | No |
| `emergency_contact_phone` | String | Exactly 10 digits | No |
| `created_at` | Timestamp | Auto-generated (UTC) | Auto |
| `updated_at` | Timestamp | Auto-updated on modification (UTC) | Auto |
| `deleted_at` | Timestamp | Nullable, for soft deletes | Auto |

## Voice Agent Configuration

See [`VOICE_AGENT_SETUP.md`](VOICE_AGENT_SETUP.md) for the complete system prompt and Vapi.ai tool schemas.

### Conversation Flow
1. Greet caller → ask for phone number
2. Look up existing record (duplicate detection)
3. Collect required fields conversationally
4. Offer optional fields (insurance, emergency contact, language)
5. Read back all info and confirm
6. Save to database → confirm success or relay error

### Edge Cases Handled
- Invalid date of birth → re-prompts specifically
- "Start over" → clears context, restarts cheerfully
- Corrections → updates specific fields
- Invalid data → re-prompts with clear guidance
- Database write failure → graceful error message to caller

## Deployment

### Option 1: Render (Recommended)

1. Push code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. New → Web Service → Connect your repo
4. Render auto-detects `render.yaml` or `Dockerfile`
5. Add environment variable: `DATABASE_URL` = your Neon connection string
6. Deploy

### Option 2: Docker

```bash
docker build -t voice-ai-api .
docker run -p 8000:8000 -e DATABASE_URL="postgresql://..." voice-ai-api
```

### Database Setup (Neon)

1. Sign up at [neon.tech](https://neon.tech) (free, no credit card)
2. Create a project
3. Copy the connection string from the Dashboard
4. Set it as `DATABASE_URL` in your environment

## Known Limitations & Trade-offs

| Limitation | Rationale |
|---|---|
| **SQLite for local dev** | Simplifies local setup. Production uses Neon PostgreSQL. |
| **No authentication on API** | Assessment scope. In production, would add API key or JWT auth. |
| **No HIPAA compliance** | Explicitly out of scope per assessment. No real patient data stored. |
| **Render free tier spin-down** | Service spins down after 15 min inactivity (30-60s cold start). Database persistence is unaffected (Neon is external). |
| **No rate limiting** | Would add in production to prevent abuse. |
| **CORS allow all origins** | Required for Vapi tool calls. In production, would whitelist specific domains. |

## Next Steps (What I'd Do With More Time)

- **Automated test suite** — Pytest with fixtures for database isolation
- **API key authentication** — Protect endpoints from unauthorized access
- **Rate limiting** — Prevent abuse with FastAPI middleware
- **Call transcript storage** — Link call summaries to patient records
- **Appointment scheduling** — Mock scheduling flow after registration
- **Dashboard UI** — Simple web interface to view registered patients
- **CI/CD pipeline** — GitHub Actions for linting, testing, and auto-deploy
- **Structured logging** — JSON logging with correlation IDs for observability
