# Technical Requirements Document (TRD)

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, CSS |
| Backend | Python, FastAPI, Pydantic |
| Database | MongoDB via PyMongo |
| AI | Provider-neutral adapter; Gemini/OpenAI/Anthropic and compatible providers |
| Integrations | Gmail API/OAuth, Tesseract OCR |
| Testing | Python `unittest`, mocked SDK/service responses |

## Architectural requirements

- Route handlers own HTTP concerns; services own integration/business helper logic.
- Pydantic models validate requests and AI-derived structures before persistence.
- AI provider calls are isolated in `backend/services/ai_client.py`.
- Frontend uses `VITE_API_BASE_URL`, defaulting to `http://127.0.0.1:8000`.
- MongoDB access is centralized in `backend/database.py`.
- No secrets may be returned by configuration/status endpoints.

## API contract principles

- Return explicit success payloads with `status: "success"` where established.
- Return user-actionable HTTP 4xx errors for invalid input, unavailable resources, or stale review items.
- Preserve existing endpoints when refactoring; add versioning/migrations before breaking contracts.
- Dates use `YYYY-MM-DD`; timestamps are ISO-8601 strings in responses.

## AI requirements

- Supported providers: `gemini`, `openai`, `anthropic`, `groq`, `mistral`, `deepseek`, `xai`, `together`.
- AI output must be parsed and validated against `AIEmailAnalysis`; invalid outputs fall back or fail safely.
- The application owns prompts, fallback logic, confidence policy, and storage decisions.
- The frontend only calls backend AI endpoints; it never exposes provider keys.

## Security requirements

- `.env`, OAuth client secrets, Fernet keys, access tokens, and personal data must not be committed.
- Gmail token records are encrypted using Fernet.
- OAuth state records have a TTL index.
- Mask sensitive numbers before AI analysis or evidence storage.
- Use HTTPS and set `OAUTHLIB_INSECURE_TRANSPORT=0` outside local development.
- Validate uploaded file types/content before OCR processing.

## Quality requirements

- Run unit tests before merging backend changes.
- Run `npm run build` after frontend changes.
- Preserve keyboard focus states, semantic controls, responsive behavior, and reduced-motion support.
- Keep charts dependency-free unless a future requirement justifies a charting library.

## Operational constraints

- The scheduler is local/in-process and is not appropriate for multiple API workers.
- For production, replace it with a single scheduled worker/queue and central secret management.
- MongoDB indexes are created on application startup.
