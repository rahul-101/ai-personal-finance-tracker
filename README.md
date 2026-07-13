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
- `backend/services/`: email parsing, OCR, and Gemini integration
- `backend/models.py`: request validation contracts
- `backend/database.py`: MongoDB collections and indexes
- `frontend/`: static dashboard

## Development checks

From `backend/`:

```bash
python -m unittest discover -s tests -v
python -m py_compile $(find . -path './venv' -prune -o -name '*.py' -print)
```

## Security notes

- Never commit `.env`, OAuth credentials, or real finance data.
- The current Gmail implementation is for one local learning user. Before deployment, add user authentication, OAuth state validation, and secure HTTPS-only configuration.
- Gemini output must be treated as untrusted data and validated before storage.
