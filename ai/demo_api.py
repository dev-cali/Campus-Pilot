"""Standalone local FastAPI demo; deliberately does not import main/database.

Run on loopback only. This public-fictional scope is not production auth.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from ai.answer_service import AnswerResponse, AnswerService, StrictModel
from ai.demo_store import DemoStore
from ai.llm_client import OpenAIAnswerGenerator
from ai.local_retrieval import KeywordRetriever, validate_question


class AskRequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        return validate_question(value)


def create_app(service: AnswerService | None = None, *, reference_date=None) -> FastAPI:
    """Inject a mocked service/date in tests; normal startup uses the real SDK."""
    store = None
    if service is None:
        store = DemoStore()
        service = AnswerService(KeywordRetriever(store), OpenAIAnswerGenerator())

    @asynccontextmanager
    async def lifespan(_app):
        # No automatic seeding or database creation. Missing seed -> unavailable.
        try:
            yield
        finally:
            if store is not None:
                store.close()

    app = FastAPI(title="CampusPilot Fictional RAG Demo", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request, _exception):
        # FastAPI's default validation details may echo input; use a neutral body.
        return JSONResponse(status_code=422, content={"detail": "Invalid question request."})

    @app.post("/api/ai/ask", response_model=AnswerResponse)
    def ask(request: AskRequest):
        today = reference_date if reference_date is not None else datetime.now(timezone.utc).date()
        result = service.ask(request.question, reference_date=today)
        if result.status == "unavailable":
            return JSONResponse(status_code=503, content=result.model_dump())
        if result.status == "denied":
            return JSONResponse(status_code=403, content=result.model_dump())
        return result

    return app


app = create_app()
