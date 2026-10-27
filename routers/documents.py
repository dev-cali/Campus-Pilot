from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import SessionLocal, Document, DocumentChunk
from schemas import document_schemas

router = APIRouter(prefix="/documents", tags=["documents"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[document_schemas.Document])
def get_documents(db: Session = Depends(get_db)):
    documents = db.query(Document).all()
    return documents


@router.get("/{document_id}", response_model=document_schemas.Document)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/", response_model=document_schemas.Document)
def create_document(document: document_schemas.DocumentCreate, db: Session = Depends(get_db)):
    db_document = Document(**document.dict())
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


@router.put("/{document_id}", response_model=document_schemas.Document)
def update_document(document_id: int, document: document_schemas.DocumentCreate, db: Session = Depends(get_db)):
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    for key, value in document.dict().items():
        setattr(db_document, key, value)
    db.commit()
    db.refresh(db_document)
    return db_document


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(db_document)
    db.commit()
    return {"message": "Document deleted successfully"}
