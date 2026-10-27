# Backend API Journal

## Current Status
- Branch: feature/backend-api (pushed to origin)
- Date: 2026-10-28
- Role: Backend/API Engineer
- State: CRUD scaffolding + ingestion endpoint added. Team clarified architecture - moving to Supabase SDK + Pinecone. SQLAlchemy currently used by existing implementation; will adopt dual approach.

## What's Done
- [x] Analyzed project structure, models, existing endpoints
- [x] Pulled latest changes from main (merged S3-03 frontend AI integration + RAG demo)
- [x] Created ackend-api/ workspace with eatures/, work/, acklogs/, docs/ folders
- [x] Pushed initial workspace to branch
- [x] Dependency analysis - SQLAlchemy used heavily by existing codebase (database.py, main.py, alembic, routers). Will retain until migration approved.
- [x] Installed required deps (fastapi, uvicorn, pydantic, sqlalchemy, httpx, openai, psycopg2-binary, psycopg)
- [x] Created API structure: outers/, schemas/ with CRUD for Users, Documents, DocumentChunks, Questions
- [x] Integrated routers into main.py without breaking existing endpoints
- [x] Added ingestion endpoint using i.document_processing.split_document_text
- [x] Documented findings in ackend-api/docs/DEPENDENCY_ANALYSIS.md
- [x] Team clarified: use Supabase SDK + Pinecone SDK, phase out SQLAlchemy over time

## What Needs to Work On (Priority)
1. [ ] **Supabase SDK setup** - Create client wrapper, configure env vars, test connection
2. [ ] **Pinecone SDK setup** - Create client wrapper for vector operations
3. [ ] **Schema alignment (BLOCKED - needs approval)** - DocumentChunk model lacks source_reference etc. Coordinate with Brian
4. [ ] **New endpoints with Supabase SDK** - Build RAG/chat features using Supabase SDK (don't rewrite existing CRUD yet)
5. [ ] **API tests for CRUD & ingestion** - Write basic tests to validate new endpoints

## Backlogs
- [ ] Authentication/Authorization (Supabase Auth integration via Supabase SDK)
- [ ] Migrate existing CRUD from SQLAlchemy to Supabase SDK (when approved)
- [ ] Migrations strategy - decide between Alembic vs Supabase migrations
- [ ] Embedding generation & Pinecone integration (Sprint 3 per docs)

## Future Implementations
- [ ] RAG ingestion pipeline (upload/extract -> process -> chunk -> embed -> store in Pinecone + metadata in Supabase)
- [ ] Chat/RAG query endpoint integrating retrieval + LLM
- [ ] Citation tracking and validation
- [ ] Rate limiting and error handling improvements
- [ ] API documentation enhancements

## Notes
- Demo RAG system exists separately (i/demo_api.py) - don't break it
- Existing endpoints in main.py must remain functional
- **Retaining SQLAlchemy for now** because it's used by existing implementation (database.py, main.py, alembic, routers). Will migrate gradually per team direction.
- Schema change requires approval per orchestrator rules (shared-schema change, Brian owns backend)
- Ingestion works with current schema by pulling title/version from Document model
- Use Supabase SDK for NEW features; don't rewrite existing code without approval
