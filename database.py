import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Credentials come from .env / the process environment. Never hardcode them here.
load_dotenv(Path(__file__).resolve().with_name(".env"))

DATABASE_URL = os.environ.get("DATABASE_URL")

_engine = None
_session_factory = None


def get_engine():
    """Return the SQLAlchemy engine, creating it on first use.

    Deferring creation keeps importing the app free of database credentials, so
    test collection and tooling work without a configured `.env`. Local and
    deployed runs behave the same once `DATABASE_URL` is set.
    """
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not set. Copy .env.example to .env and set DATABASE_URL "
                "to your Postgres/Supabase connection string."
            )
        _engine = create_engine(DATABASE_URL)
    return _engine


def SessionLocal(**kwargs):
    """Session factory, bound to the engine on first call rather than on import."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return _session_factory(**kwargs)


Base = declarative_base()

# (Keep your model classes User, Department, Document, etc. below this)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False)
    questions = relationship("Question", back_populates="user")

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    documents = relationship("Document", back_populates="department")
    questions = relationship("Question", back_populates="department")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    title = Column(String, nullable=False)
    version = Column(String, nullable=False)
    effective_date = Column(Date, nullable=False)
    status = Column(String, nullable=False)
    
    department = relationship("Department", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    page_no = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    # Embedding stored as text or vector format depending on setup
    embedding = Column(Text, nullable=True)
    source_reference = Column(String, nullable=True)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=True)
    
    document = relationship("Document", back_populates="chunks")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True)
    
    user = relationship("User", back_populates="questions")
    department = relationship("Department", back_populates="questions")
