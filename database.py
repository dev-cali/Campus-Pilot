import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Directly paste your Supabase session pooler URL with your actual password here:
DATABASE_URL = "postgresql://postgres:cPPilot2026@db.gafztbgjhugbgcpnyyto.supabase.co:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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