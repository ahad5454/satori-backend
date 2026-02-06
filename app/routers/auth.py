from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.admin import Admin
from app.schemas.auth import AdminCreate, AdminLogin, Token
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(tags=["Authentication"])

@router.post("/signup", response_model=Token)
def signup(admin: AdminCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing = db.query(Admin).filter(Admin.email == admin.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_admin = Admin(
        email=admin.email,
        username=admin.email.split("@")[0],  
        hashed_password=hash_password(admin.password)
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    token = create_access_token({"sub": new_admin.email, "role": new_admin.role})
    return {"access_token": token, "token_type": "bearer", "role": new_admin.role}


@router.post("/signin", response_model=Token)
def signin(data: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == data.email).first()

    if not admin or not verify_password(data.password, admin.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": admin.email, "role": admin.role})
    return {"access_token": token, "token_type": "bearer", "role": admin.role}
