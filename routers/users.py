from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List

from auth import require_staff
from database import User, Department, get_db
from schemas import document_schemas

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[document_schemas.User])
def get_users(
    _staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    # User rows carry names and email addresses, so they are staff-only.
    users = db.query(User).all()
    return users


@router.get("/{user_id}", response_model=document_schemas.User)
def get_user(
    user_id: int,
    _staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=document_schemas.User)
def create_user(
    user: document_schemas.UserCreate,
    _staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    db_user = User(**user.model_dump())
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        # The only unique column on users is email; report a conflict rather
        # than letting the constraint surface as a 500.
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A user with this email already exists"
        )
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    _staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}
