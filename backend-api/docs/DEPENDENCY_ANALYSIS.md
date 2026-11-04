# Dependency Analysis for CampusPilot Backend

## Current Implementation Review

### What's actually used:
**main.py (shared FastAPI app):**
- fastapi (FastAPI, Depends, HTTPException, CORSMiddleware) - YES NEEDED
- sqlalchemy.orm (Session) - used with SessionLocal from database.py
- database (SessionLocal, User, Department) - imports models
- openai (OpenAI) - for /test-ai endpoint

**database.py:**
- sqlalchemy (create_engine, Column, types, ForeignKey, JSON, declarative_base, sessionmaker, relationship) - YES NEEDED currently
- Connects to Supabase Postgres via SQLAlchemy

**ai/demo_api.py & ai/demo_store.py:**
- fastapi, pydantic, sqlalchemy - all used by demo app
- These are separate from main.py but part of the codebase

**ai/llm_client.py:**
- openai - for actual LLM calls
- pydantic - for validation

**alembic:**
- Uses SQLAlchemy models

### Team's stated direction:
- "Our team previously decided to remove SQLAlchemy and use Supabase instead, although PostgreSQL remains the underlying database"
- Stack includes: FastAPI, Supabase (PostgreSQL, Auth, Storage), Pinecone

### Recommendation:

**For CURRENT codebase (preserve existing architecture):**
We MUST keep these installed to run existing code:
- fastapi - core framework, used everywhere
- uvicorn - ASGI server to run FastAPI
- pydantic - used by FastAPI and validation throughout
- sqlalchemy - used by main.py, database.py, alembic, demo_store
- httpx - needed for TestClient (used by tests), also common for async HTTP
- openai - used in main.py /test-ai and ai/llm_client.py

**For NEW direction (Supabase + Pinecone):**
- supabase-py (or 'supabase') - Supabase Python client for Auth/DB/Storage when migrating from SQLAlchemy
- pinecone-client (or 'pinecone') - Vector DB client for RAG
- These are NOT currently used but align with target stack

**But the instruction says:** "determine whether FastAPI, Uvicorn, Pydantic, SQLAlchemy, and HTTPX are actually needed based on the current implementation. Also check whether we need the Supabase and Pinecone Python SDKs. Explain your recommended dependencies briefly, avoid unnecessary installations, and preserve our group's existing architecture."

So for the CURRENT implementation - all of FastAPI, Uvicorn, Pydantic, SQLAlchemy, HTTPX ARE needed. Supabase and Pinecone SDKs are NOT currently used, so not strictly necessary yet. But they ARE in our agreed stack. Installing them now won't hurt and might be needed soon. Better to be prepared but minimal.

**Safest approach:**
1. Install what's needed to run current tests and code: fastapi, uvicorn[standard], pydantic, sqlalchemy, httpx, openai
2. Also consider psycopg2-binary or psycopg for connecting to Postgres (Supabase uses Postgres). The connection string uses postgresql:// - SQLAlchemy needs a driver.
3. Add supabase and pinecone-client if they might be needed soon? The instruction says "check whether we need the Supabase and Pinecone Python SDKs" - better to explain and maybe hold off unless needed. But easier to add minimal ones.

Also check if psycopg2 is needed - let us look up how it's connecting.
"postgresql://postgres:..." - SQLAlchemy with psycopg2 by default needs psycopg2. It's not installed. That could be an issue. But in the environment, maybe it's installed differently? Or maybe we need it.

But better to be conservative and install what's needed for current architecture to work.
