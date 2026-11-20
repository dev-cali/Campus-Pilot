from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from auth import get_current_user, require_staff
from database import DocumentChunk, Document, User, get_db
from schemas import document_schemas

router = APIRouter(prefix="/chunks", tags=["chunks"])


@router.get("/", response_model=List[document_schemas.DocumentChunk])
def get_chunks(
    document_id: int = None,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(DocumentChunk)
    if document_id is not None:
        query = query.filter(DocumentChunk.document_id == document_id)
    chunks = query.all()
    return chunks


@router.get("/{chunk_id}", response_model=document_schemas.DocumentChunk)
def get_chunk(
    chunk_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk


@router.post("/", response_model=document_schemas.DocumentChunk)
def create_chunk(
    chunk: document_schemas.DocumentChunkCreate,
    _user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    if db.query(Document).filter(Document.id == chunk.document_id).first() is None:
        raise HTTPException(status_code=404, detail="Document not found")
    db_chunk = DocumentChunk(**chunk.model_dump())
    db.add(db_chunk)
    db.commit()
    db.refresh(db_chunk)
    return db_chunk


@router.delete("/{chunk_id}")
def delete_chunk(
    chunk_id: int,
    _user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    db_chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
    if db_chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")
    db.delete(db_chunk)
    db.commit()
    return {"message": "Chunk deleted successfully"}
