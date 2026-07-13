import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.gemini_models import router as gemini_models_router
from routes.dashboard import router as dashboard_router
from routes.uploads import router as uploads_router
from routes.export import router as export_router

from database import check_mongodb_connection, create_database_indexes
from routes.transactions import router as transactions_router
from routes.gmail_auth import router as gmail_auth_router
from routes.gmail_sync import router as gmail_sync_router
from routes.ai_test import router as ai_test_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        create_database_indexes()
    except Exception:
        # The health endpoint remains available so a local configuration problem
        # is diagnosable, while the full error stays in server logs.
        logger.exception("MongoDB indexes could not be initialized")
    yield


app = FastAPI(
    title="AI Personal Finance Tracker API",
    description="FastAPI backend for AI Personal Finance Tracker",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS"
    ],
    allow_headers=[
        "Content-Type",
        "Authorization"
    ]
)


@app.get("/")
def health_check():
    return {
        "message": "AI Personal Finance Tracker API is running"
    }


@app.get("/db-check")
def db_check():
    is_connected = check_mongodb_connection()

    if is_connected:
        return {
            "status": "success",
            "message": "MongoDB connected successfully"
        }

    return {
        "status": "failed",
        "message": "MongoDB connection failed"
    }


app.include_router(transactions_router)

app.include_router(gmail_auth_router)

app.include_router(gmail_sync_router)

app.include_router(ai_test_router)

app.include_router(gemini_models_router)

app.include_router(dashboard_router)

app.include_router(uploads_router)

app.include_router(export_router)
