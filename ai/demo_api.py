
"""Standalone fictional FastAPI RAG demo.

Independent of the main application and production database.
Server-to-server authentication is required by default.
Public deployment additionally requires restricted frontend access
and request quotas. Not a production university information system.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import sqlite3
import logging
import json

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from ai.answer_service import AnswerResponse, AnswerService, StrictModel
from ai.demo_security import require_demo_secret
from ai.demo_rate_limit import create_demo_rate_limiter
from ai.demo_store import DemoStore
from ai.llm_client import OpenAIAnswerGenerator, configuration_diagnostics
from ai.local_retrieval import validate_question
from ai.pinecone_retrieval import create_retriever


class AskRequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        return validate_question(value)


def create_app(
    service: AnswerService | None = None,
    *,
    reference_date=None,
    require_auth: bool = True,
) -> FastAPI:
    """Inject a mocked service/date in tests; normal startup uses the real SDK."""

    store = None

    if service is None:
        store = DemoStore()

        def check_readiness():
            # Read-only probe. Does not initialize or seed the database.
            connection = sqlite3.connect(
                store.path.as_uri() + "?mode=ro",
                uri=True,
                timeout=2.0,
            )

            try:
                connection.execute(
                    "SELECT document_id, record FROM demo_documents LIMIT 0"
                )

                connection.execute(
                    "SELECT document_id, page_no, chunk_index, chunk_text, "
                    "start_char, end_char FROM demo_chunks LIMIT 0"
                )
            finally:
                connection.close()

        service = AnswerService(
            create_retriever(store),
            OpenAIAnswerGenerator(),
            readiness_check=check_readiness,
        )

    @asynccontextmanager
    async def lifespan(_app):
        # No automatic seeding or database creation.
        if store is not None:
            logging.getLogger("uvicorn.error").warning(
                "AI configuration: %s",
                json.dumps(configuration_diagnostics()),
            )

        try:
            yield
        finally:
            if store is not None:
                store.close()

    app = FastAPI(
        title="CampusPilot Fictional RAG Demo",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request, _exception):
        # Prevent validation errors from exposing submitted input.
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid question request."},
        )

    # Create one rate limiter for this application instance.
    rate_limiter = create_demo_rate_limiter()

    @app.post(
        "/api/ai/ask",
        response_model=AnswerResponse,
        dependencies=[
            Depends(require_demo_secret),
            Depends(rate_limiter.check),
        ] if require_auth else [],
    )
    def ask(request: AskRequest):
        today = (
            reference_date
            if reference_date is not None
            else datetime.now(timezone.utc).date()
        )

        result = service.ask(
            request.question,
            reference_date=today,
        )

        if result.status == "unavailable":
            return JSONResponse(
                status_code=503,
                content=result.model_dump(),
            )

        if result.status == "denied":
            return JSONResponse(
                status_code=403,
                content=result.model_dump(),
            )

        return result

    return app


app = create_app()
