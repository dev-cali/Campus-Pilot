from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    name: str
    email: str
    role: str


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int

    class Config:
        from_attributes = True


class DepartmentBase(BaseModel):
    name: str


class DepartmentCreate(DepartmentBase):
    pass


class Department(DepartmentBase):
    id: int

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    department_id: int
    title: str
    version: str
    effective_date: date
    status: str


class DocumentCreate(DocumentBase):
    pass


class Document(DocumentBase):
    id: int

    class Config:
        from_attributes = True


class DocumentChunkBase(BaseModel):
    document_id: int
    page_no: int
    chunk_text: str
    embedding: Optional[str] = None
    source_reference: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    chunk_index: Optional[int] = None


class DocumentChunkCreate(DocumentChunkBase):
    pass


class DocumentChunk(DocumentChunkBase):
    id: int

    class Config:
        from_attributes = True


class QuestionBase(BaseModel):
    user_id: int
    department_id: int
    query: str
    answer: str
    citations: Optional[dict] = None


class QuestionCreate(QuestionBase):
    pass


class Question(QuestionBase):
    id: int

    class Config:
        from_attributes = True
