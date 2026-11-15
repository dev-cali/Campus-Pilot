import logging
import os
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from sqlalchemy.orm import Session

from auth import get_current_user, require_staff
from database import Department, User, get_db
from routers import documents, chunks, questions, users, ingest

logger = logging.getLogger(__name__)

# The frontend dev server. Deployed origins belong in ALLOWED_ORIGINS.
DEFAULT_ORIGINS = "http://localhost:3000"


def get_allowed_origins() -> List[str]:
    """Parse the comma-separated ALLOWED_ORIGINS setting.

    Credentials are enabled, and browsers reject `*` together with credentials,
    so the value must be an explicit list of frontend origins.
    """
    raw = os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS)
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or [DEFAULT_ORIGINS]


app = FastAPI(title="Campus Pilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    # Liveness probe: intentionally public so hosts can check the process
    # without credentials, and it exposes no data.
    return {"message": "Campus Pilot backend is running successfully!"}


@app.get("/departments")
def get_departments(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    departments = db.query(Department).all()
    return {"departments": departments}


@app.get("/test-ai")
def test_ai(_user: User = Depends(require_staff)):
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503, detail="AI provider is not configured on this server."
        )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'AI connection successful!'"}],
            max_tokens=10,
        )
        return {"ai_response": response.choices[0].message.content}
    except Exception:
        # Provider errors can include URLs, headers and key fragments. Log the
        # real error server side and return a neutral message.
        logger.exception("AI provider connection check failed")
        raise HTTPException(
            status_code=503, detail="AI provider is unavailable. Try again later."
        )


app.include_router(users.router)
app.include_router(documents.router)
app.include_router(chunks.router)
app.include_router(questions.router)


app.include_router(ingest.router)
