import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, User, Department
from openai import OpenAI

app = FastAPI(title="Campus Pilot API")

# Enable CORS so your Next.js frontend can communicate with this backend without blocking
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Campus Pilot backend is running successfully!"}

# 1. Minimal backend endpoint reading from the database
@app.get("/departments")
def get_departments(db: Session = Depends(get_db)):
    departments = db.query(Department).all()
    return {"departments": departments}

# 2. Test call to your AI provider to confirm keys work
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