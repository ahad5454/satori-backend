from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas
from app.seed.seed_lab_fees import seed_lab_fees

router = APIRouter()

# Laboratories

@router.get("/labs/", response_model=List[schemas.Laboratory])
def get_labs(db: Session = Depends(get_db)):
    return db.query(models.Laboratory).all()


@router.post("/labs/", response_model=schemas.Laboratory)
def create_lab(lab: schemas.LaboratoryCreate, db: Session = Depends(get_db)):
    new_lab = models.Laboratory(
        name=lab.name,
        address=lab.address,
        contact_info=lab.contact_info
    )
    db.add(new_lab)
    db.commit()
    db.refresh(new_lab)
    return new_lab


# Service Categories (linked to Labs)

@router.get("/categories/", response_model=List[schemas.ServiceCategory])
def get_service_categories(lab_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.ServiceCategory)
    if lab_id:
        query = query.filter(models.ServiceCategory.lab_id == lab_id)
    return query.all()


@router.post("/categories/", response_model=schemas.ServiceCategory)
def create_service_category(category: schemas.ServiceCategoryCreate, db: Session = Depends(get_db)):
    lab = db.query(models.Laboratory).filter(models.Laboratory.id == category.lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    new_category = models.ServiceCategory(
        name=category.name,
        description=category.description,
        lab_id=category.lab_id
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


# Tests (linked to Service Categories)

@router.get("/tests/", response_model=List[schemas.Test])
def get_tests(service_category_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Test)
    if service_category_id:
        query = query.filter(models.Test.service_category_id == service_category_id)
    return query.all()


@router.post("/tests/", response_model=schemas.Test)
def create_test(test: schemas.TestCreate, db: Session = Depends(get_db)):
    category = db.query(models.ServiceCategory).filter(models.ServiceCategory.id == test.service_category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Service category not found")

    new_test = models.Test(
        name=test.name,
        service_category_id=test.service_category_id
    )
    db.add(new_test)
    db.commit()
    db.refresh(new_test)
    return new_test


# Turnaround Times

@router.get("/turn_times/", response_model=List[schemas.TurnTime])
def get_turn_times(db: Session = Depends(get_db)):
    return db.query(models.TurnTime).all()


@router.post("/turn_times/", response_model=schemas.TurnTime)
def create_turn_time(time: schemas.TurnTimeCreate, db: Session = Depends(get_db)):
    new_time = models.TurnTime(label=time.label, hours=time.hours)
    db.add(new_time)
    db.commit()
    db.refresh(new_time)
    return new_time


# Rates (linked to Lab + Test + Turnaround Time)

@router.get("/rates/", response_model=List[schemas.Rate])
def get_rates(
    lab_id: Optional[int] = None,
    service_category_id: Optional[int] = None,
    test_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Rate)

    if lab_id:
        query = query.filter(models.Rate.lab_id == lab_id)
    if service_category_id:
        query = query.join(models.Test).join(models.ServiceCategory).filter(
            models.ServiceCategory.id == service_category_id
        )
    if test_id:
        query = query.filter(models.Rate.test_id == test_id)

    return query.all()


@router.post("/rates/", response_model=schemas.Rate)
def create_rate(rate: schemas.RateCreate, db: Session = Depends(get_db)):
    test = db.query(models.Test).filter(models.Test.id == rate.test_id).first()
    turn_time = db.query(models.TurnTime).filter(models.TurnTime.id == rate.turn_time_id).first()
    lab = db.query(models.Laboratory).filter(models.Laboratory.id == rate.lab_id).first()

    if not test or not turn_time or not lab:
        raise HTTPException(status_code=404, detail="Invalid test, turnaround time, or laboratory")

    new_rate = models.Rate(
        test_id=rate.test_id,
        turn_time_id=rate.turn_time_id,
        lab_id=rate.lab_id,
        price=rate.price
    )
    db.add(new_rate)
    db.commit()
    db.refresh(new_rate)
    return new_rate


@router.get("/rates/by_lab/{lab_id}", response_model=List[schemas.Rate])
def get_rates_by_lab(lab_id: int, db: Session = Depends(get_db)):
    rates = db.query(models.Rate).filter(models.Rate.lab_id == lab_id).all()
    if not rates:
        raise HTTPException(status_code=404, detail="No rates found for this lab")
    return rates


@router.get("/rates/by_category/{service_category_id}", response_model=List[schemas.Rate])
def get_rates_by_category(service_category_id: int, db: Session = Depends(get_db)):
    query = (
        db.query(models.Rate)
        .join(models.Test)
        .filter(models.Test.service_category_id == service_category_id)
    )
    return query.all()


# Seed Data

@router.post("/seed")
def seed_data():
    """Seed the database with Lab1 data"""
    try:
        seed_lab_fees()
        return {"message": "Database seeded successfully with Lab1 data"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding database: {str(e)}")
