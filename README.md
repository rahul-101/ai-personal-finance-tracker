# FinSight — AI Personal Finance Tracker

FinSight is a private, single-user personal-finance workspace. It collects transactions from manual entry, Gmail alerts, receipt OCR, and bill uploads; classifies them with configurable AI providers; and presents financial summaries, budgets, reports, and review workflows.

This repository is intentionally designed to be understandable by a human developer and usable as context for another AI coding assistant.

## Documentation map

- [Product requirements](docs/PRD.md)
- [Technical requirements](docs/TRD.md)
- [Application flow](docs/APP_FLOW.md)
- [UI/UX brief](docs/UI_UX_BRIEF.md)
- [Backend schema](docs/BACKEND_SCHEMA.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)

## Current capabilities

- Manual transactions with status, financial type, date-range, category, and search filters.
- Financial types: income, expense, investment, transfer, refund, plus legacy debit/credit.
- Gmail OAuth connection, manual sync, optional local daily/weekly scheduled sync, and sync history.
- Gmail low-confidence review: approve/add, edit/add, or ignore an email before it affects records.
- Receipt and bill image uploads, OCR, optional AI enrichment, bill history, and unpaid bill tracking.
- Transaction review workflow: `review_required` → `confirmed` or `rejected`.
- Dashboard KPIs, financial-health meter, interactive HTML/CSS charts, budgets, reports, weekly AI digest/advice, exports, and profile preferences.
- Provider-neutral AI support for Gemini, OpenAI, Anthropic, Groq, Mistral, DeepSeek, xAI, and Together AI. Ollama is intentionally not included.
- React/Vite premium dashboard with dark mode and responsive layouts.

## Repository layout

```text
backend/             FastAPI app, MongoDB access, models, routes, services, tests
frontend-react/      Primary React/Vite frontend
frontend/            Legacy static frontend retained for reference
docs/                Product and technical context for humans and AI assistants
```

## Local setup

### Backend

Requirements: Python 3.11+, MongoDB Atlas or local MongoDB, and Tesseract OCR for image extraction.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

API: `http://127.0.0.1:8000`
Interactive API docs: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend-react
npm install
npm run dev
```

Open `http://localhost:3000`.

Build the frontend with:

```bash
npm run build
```

## Environment configuration

Copy `backend/.env.example` to `backend/.env`. Required configuration includes:

```env
MONGO_URI=...
DATABASE_NAME=finance_tracker
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback
FERNET_KEY=...

AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-flash
AI_API_KEY=...
```

`AI_API_KEY` can be replaced with a matching provider-specific variable such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GROQ_API_KEY`. Never commit `.env`, OAuth secrets, tokens, or personal finance data.

## Development checks

Backend tests:

```bash
cd backend
source venv/bin/activate
python -m unittest discover -s tests -v
```

The current suite covers provider adapters, financial summaries, budgets, review workflows, Gmail status/scheduling/log review, validation, and upload validation.

## Architecture summary

```text
React/Vite UI
    ↓ HTTP
FastAPI routes → Pydantic validation → services → MongoDB
                               ↘ AI provider adapter
                                ↘ Gmail / OCR integrations
```

The frontend must not call AI providers, MongoDB, or Gmail directly. The backend validates all incoming data and treats AI output as untrusted before persistence.

## Known constraints

- This is a single-user local application, not a multi-user SaaS.
- The automatic Gmail scheduler is in-process and runs only while the FastAPI server is running. It is suitable for local use, not multi-worker production deployment.
- `frontend-react/src/App.tsx` is currently a large composition file. Future refactoring should split it into pages/components without altering APIs.

## Guidance for another AI assistant

1. Read `README.md` and the relevant file in `docs/` before proposing changes.
2. Preserve the current REST routes and model validation unless a migration is explicitly planned.
3. Prefer small, testable steps. Add backend tests for route/service changes.
4. Do not add Ollama support unless the user explicitly changes the project decision.
5. Do not store secrets, raw card numbers, PINs, bank credentials, or unmasked sensitive email content.
6. Treat any AI response as untrusted; validate it with the established Pydantic/domain flow.
