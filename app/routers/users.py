from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models.admin import Admin
from app.core.security import hash_password, get_current_user

router = APIRouter(
    prefix="/users",
    tags=["User Management"]
)

# Pydantic Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str # 'admin', 'manager', 'user'

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    role: str
    
    class Config:
        orm_mode = True

# Dependency to check if current user is admin
def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to access user management"
        )
    return current_user

@router.get("/", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    """List all users. Only for Admins."""
    users = db.query(Admin).all()
    return users

@router.post("/", response_model=UserOut)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    """Create a new user. Only for Admins."""
    # Check existing
    if db.query(Admin).filter(Admin.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Validate role
    if user_in.role not in ["admin", "manager", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin', 'manager', or 'user'")

    new_user = Admin(
        email=user_in.email,
        username=user_in.email.split("@")[0],
        hashed_password=hash_password(user_in.password),
        role=user_in.role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    """Delete a user. Only for Admins."""
    user = db.query(Admin).filter(Admin.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Prevent deleting yourself (compare email since current_user is a dict)
    if user.email == current_user["email"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
