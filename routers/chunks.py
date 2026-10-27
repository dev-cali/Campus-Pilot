from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import SessionLocal, DocumentChunk
from schemas import document_schemas

router = APIRouter(prefix="/chunks", tags=["chunks"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[document_schemas.DocumentChunk])
def get_chunks(document_id: int = None, db: Session = Depends(get_db)):
    query = db.query(DocumentChunk)
    if document_id is not None:
        query = query.filter(DocumentChunk.document_id == document_id)
    chunks = query.all()
    return chunks


@router.get("/{chunk_id}", response_model=document_schemas.DocumentChunk)
def get_chunk(chunk_id: int, db: Session = Depends(get_db)):
    chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk


@router.post("/", response_model=document_schemas.DocumentChunk)
def create_chunk(chunk: document_schemas.DocumentChunkCreate, db: Session = Depends(get_db)):
    db_chunk = DocumentChunk(**chunk.dict())
    db.add(db_chunk)
    db.commit()
    db.refresh(db_chunk)
    return db_chunk


@router.delete("/{chunk_id}")
def delete_chunk(chunk_id: int, db: Session = Depends(get_db)):
    db_chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
    if db_chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")
    db.delete(db_chunk)
    db.commit()
    return {"message": "Chunk deleted successfully"}
