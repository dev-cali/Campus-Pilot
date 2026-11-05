from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from auth import STAFF_ROLES, get_current_user, require_staff
from database import Question, User, Department, get_db
from schemas import document_schemas

router = APIRouter(prefix="/questions", tags=["questions"])


def _is_staff(user: User) -> bool:
    return (user.role or "").strip().lower() in STAFF_ROLES


@router.get("/", response_model=List[document_schemas.Question])
def get_questions(
    _user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    # Rows contain other students' questions and answers, so listing them is
    # staff-only until a filtered "my questions" endpoint exists.
    questions = db.query(Question).all()
    return questions


@router.get("/{question_id}", response_model=document_schemas.Question)
def get_question(
    question_id: int,
    _user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.post("/", response_model=document_schemas.Question)
def create_question(
    question: document_schemas.QuestionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # A student may only record questions against their own account; staff can
    # record on someone else's behalf.
    effective_user_id = question.user_id if _is_staff(user) else user.id

    if db.query(User).filter(User.id == effective_user_id).first() is None:
        raise HTTPException(status_code=404, detail="User not found")
    if db.query(Department).filter(Department.id == question.department_id).first() is None:
        raise HTTPException(status_code=404, detail="Department not found")

    values = question.model_dump()
    values["user_id"] = effective_user_id
    db_question = Question(**values)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


@router.delete("/{question_id}")
def delete_question(
    question_id: int,
    _user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    db_question = db.query(Question).filter(Question.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(db_question)
    db.commit()
    return {"message": "Question deleted successfully"}
