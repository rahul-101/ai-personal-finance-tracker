# AI Personal Finance Tracker

A learning project that imports personal-finance data from manual entry, Gmail transaction alerts, receipt OCR, and bill uploads. The backend uses FastAPI and MongoDB; the frontend is a small static dashboard.

## Current capabilities

- Manual transaction creation and paginated transaction listing
- Gmail OAuth token storage with Fernet encryption and transaction-email parsing
- Receipt and bill OCR with optional Gemini enrichment
- Dashboard summaries plus CSV and JSON exports

## Local setup

1. Install Python 3.11+ and the [Tesseract OCR](https://tesseract-ocr.github.io/tessdoc/Installation.html) executable.
2. Create and activate a virtual environment inside `backend/`.
3. Install dependencies with `pip install -r requirements.txt`.
4. Copy `backend/.env.example` to `backend/.env`, then set the required secrets.
5. Start the API from `backend/`:

   ```bash
   uvicorn main:app --reload
   ```

6. Serve `frontend/` with a local static server, for example:

   ```bash
   python -m http.server 3000 --directory frontend
   ```

Open `http://127.0.0.1:3000`. FastAPI documentation is at `http://127.0.0.1:8000/docs`.

## Architecture

- `backend/routes/`: HTTP endpoints
- `backend/services/`: email parsing, OCR, and AI-provider integration
- `backend/services/ai_client.py`: provider-neutral AI adapter selected by environment configuration
- `backend/models.py`: request validation contracts
- `backend/database.py`: MongoDB collections and indexes
- `frontend/`: static dashboard

## Development checks

From `backend/`:

```bash
python -m unittest discover -s tests -v
python -m py_compile $(find . -path './venv' -prune -o -name '*.py' -print)
```

## AI provider configuration

AI-backed email classification and receipt/bill extraction share one provider-neutral
client. The application owns the prompts, fallback behavior, and validation; the
configured provider only generates a response. Gemini remains the default for
backward compatibility.

Set these values in `backend/.env`:

```env
AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-flash
AI_API_KEY=your-provider-key
AI_BASE_URL=
```

Supported values for `AI_PROVIDER` are `gemini`, `openai`, `anthropic`, and
`ollama`. OpenAI and Anthropic SDKs are optional dependencies; install their SDK
when selecting either provider. Ollama uses its local HTTP API and defaults to
`http://127.0.0.1:11434` when `AI_BASE_URL` is empty. Existing `GEMINI_API_KEY`
and `GEMINI_MODEL` settings continue to work during migration.

The dashboard Settings panel reads `GET /ai/configuration` and can run a small
provider health check through `POST /ai/test`. Neither endpoint returns API keys.

## Security notes

- Never commit `.env`, OAuth credentials, or real finance data.
- The current Gmail implementation is for one local learning user. Before deployment, add user authentication, OAuth state validation, and secure HTTPS-only configuration.
- Gemini output must be treated as untrusted data and validated before storage.
