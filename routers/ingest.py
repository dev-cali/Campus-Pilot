from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from database import SessionLocal, Document, DocumentChunk
from ai.document_processing import split_document_text

router = APIRouter(prefix='/ingest', tags=['ingestion'])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class IngestPageRequest(BaseModel):
    document_id: int
    page_no: int
    text: str
    source_reference: str
    max_chars: int = 1000


@router.post('/chunk')
def ingest_page(request: IngestPageRequest, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail='Document not found')
    
    try:
        chunks = split_document_text(
            request.text,
            document_id=request.document_id,
            page_no=request.page_no,
            source_reference=request.source_reference,
            title=document.title,
            version=document.version,
            max_chars=request.max_chars,
        )
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    created_chunks = []
    for chunk in chunks:
        db_chunk = DocumentChunk(
            document_id=chunk.document_id,
            page_no=chunk.page_no,
            chunk_text=chunk.chunk_text,
        )
        db.add(db_chunk)
        db.commit()
        db.refresh(db_chunk)
        created_chunks.append({
            'id': db_chunk.id,
            'chunk_index': chunk.chunk_index,
            'chunk_text': chunk.chunk_text,
            'start_char': chunk.start_char,
            'end_char': chunk.end_char,
        })
    
    return {'created': len(created_chunks), 'chunks': created_chunks}
