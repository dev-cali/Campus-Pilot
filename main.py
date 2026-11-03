import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, User, Department
from openai import OpenAI

from routers import documents, chunks, questions, users, ingest

app = FastAPI(title="Campus Pilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Campus Pilot backend is running successfully!"}

@app.get("/departments")
def get_departments(db: Session = Depends(get_db)):
    departments = db.query(Department).all()
    return {"departments": departments}

@app.get("/test-ai")
def test_ai():
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI_API_KEY not found in environment variables")
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'AI connection successful!'"}],
            max_tokens=10
        )
        return {"ai_response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(users.router)
app.include_router(documents.router)
app.include_router(chunks.router)
app.include_router(questions.router)


app.include_router(ingest.router)

