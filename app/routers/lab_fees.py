from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas
from app.models.hrs_estimator import LaborRate
from app.seed.seed_lab_fees import seed_lab_fees
from app.utils.project_summary import save_or_update_module_summary
from app.utils.estimate_snapshot import save_module_to_snapshot

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


@router.delete("/categories/{category_id}", status_code=204)
def delete_service_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(models.ServiceCategory).filter(models.ServiceCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Service category not found")
    
    # Manually cascade delete: Rates -> Tests -> Category
    # 1. Find all tests in this category
    tests = db.query(models.Test).filter(models.Test.service_category_id == category_id).all()
    
    for test in tests:
        # 2. Delete all rates for each test
        db.query(models.Rate).filter(models.Rate.test_id == test.id).delete()
    
    # 3. Delete all tests
    db.query(models.Test).filter(models.Test.service_category_id == category_id).delete()
    
    # 4. Delete the category
    db.delete(category)
    db.commit()
    return None


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


@router.delete("/tests/{test_id}", status_code=204)
def delete_test(test_id: int, db: Session = Depends(get_db)):
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Manually cascade delete: Rates -> Test
    db.query(models.Rate).filter(models.Rate.test_id == test_id).delete()
    
    db.delete(test)
    db.commit()
    return None


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


# Lab Fees Orders with Staff Assignments

@router.post("/orders/", response_model=schemas.LabFeesOrder)
def create_lab_fees_order(order: schemas.LabFeesOrderCreate, db: Session = Depends(get_db)):
    """Create a lab fees order with staff assignments and calculate costs"""
    
    # Calculate total samples and lab fees cost from order_details
    total_samples = 0.0
    total_lab_fees_cost = 0.0
    
    if order.order_details:
        # order_details should contain test selections with quantities
        # Format: {"test_id": {"turn_time_id": quantity, ...}, ...}
        for test_id_str, turn_times in order.order_details.items():
            test_id = int(test_id_str)
            for turn_time_id_str, quantity in turn_times.items():
                turn_time_id = int(turn_time_id_str)
                qty = float(quantity)
                
                # Find the rate
                rate = db.query(models.Rate).filter(
                    models.Rate.test_id == test_id,
                    models.Rate.turn_time_id == turn_time_id
                ).first()
                
                if rate:
                    total_samples += qty
                    total_lab_fees_cost += rate.price * qty
    
    # Create order
    new_order = models.LabFeesOrder(
        project_name=order.project_name,
        hrs_estimation_id=order.hrs_estimation_id,
        order_details=order.order_details,
        total_samples=total_samples,
        total_lab_fees_cost=total_lab_fees_cost,
        total_staff_labor_cost=0.0,
        total_cost=total_lab_fees_cost
    )
    db.add(new_order)
    db.flush()  # Get order.id
    
    # Process staff assignments
    staff_breakdown = []
    staff_labor_costs = {}
    total_staff_labor_cost = 0.0
    
    if order.staff_assignments:
        for staff_data in order.staff_assignments:
            # Get labor rate for this role
            labor_rate = db.query(LaborRate).filter(
                LaborRate.labor_role == staff_data.role
            ).first()
            
            if not labor_rate:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid role: {staff_data.role}. Role not found in labor rates."
                )
            
            # Calculate costs
            total_hours = staff_data.count * staff_data.hours_per_person
            total_cost = total_hours * labor_rate.hourly_rate
            
            # Create staff assignment
            staff_assignment = models.LabFeesStaffAssignment(
                order_id=new_order.id,
                role=staff_data.role,
                count=staff_data.count,
                hours_per_person=staff_data.hours_per_person,
                total_hours=total_hours,
                hourly_rate=labor_rate.hourly_rate,
                total_cost=total_cost
            )
            db.add(staff_assignment)
            
            # Update summaries
            staff_breakdown.append({
                "role": staff_data.role,
                "count": staff_data.count,
                "total_hours": total_hours
            })
            
            if staff_data.role in staff_labor_costs:
                staff_labor_costs[staff_data.role] += total_cost
            else:
                staff_labor_costs[staff_data.role] = total_cost
            
            total_staff_labor_cost += total_cost
    
    # Update order totals
    new_order.total_staff_labor_cost = total_staff_labor_cost
    new_order.total_cost = total_lab_fees_cost + total_staff_labor_cost
    new_order.staff_breakdown = staff_breakdown
    new_order.staff_labor_costs = staff_labor_costs
    
    db.commit()
    db.refresh(new_order)
    
    # Save/update project estimate summary
    # Note: This happens after commit to ensure the order is persisted
    save_or_update_module_summary(
        db=db,
        project_name=order.project_name,
        module_name="lab",
        estimate_total=new_order.total_cost or 0.0,
        estimate_breakdown={
            "total_lab_fees_cost": new_order.total_lab_fees_cost,
            "total_staff_labor_cost": new_order.total_staff_labor_cost,
            "total_samples": new_order.total_samples,
            "staff_breakdown": new_order.staff_breakdown,
            "staff_labor_costs": new_order.staff_labor_costs
        }
    )
    
    # Save to estimate snapshot (full inputs + outputs for form rehydration)
    try:
        inputs_dict = order.model_dump() if hasattr(order, 'model_dump') else order.dict()
    except:
        inputs_dict = order.dict() if hasattr(order, 'dict') else {}
    
    outputs_dict = {
        "id": new_order.id,
        "project_name": new_order.project_name,
        "hrs_estimation_id": new_order.hrs_estimation_id,
        "total_cost": new_order.total_cost,
        "total_lab_fees_cost": new_order.total_lab_fees_cost,
        "total_staff_labor_cost": new_order.total_staff_labor_cost,
        "total_samples": new_order.total_samples,
        "order_details": new_order.order_details,
        "staff_breakdown": new_order.staff_breakdown,
        "staff_labor_costs": new_order.staff_labor_costs,
        "created_at": new_order.created_at.isoformat() if new_order.created_at else None,
    }
    save_module_to_snapshot(
        db=db,
        project_name=order.project_name,
        module_name="lab",
        inputs=inputs_dict,
        outputs=outputs_dict
    )
    
    db.commit()
    
    return new_order


@router.get("/orders/{order_id}", response_model=schemas.LabFeesOrder)
def get_lab_fees_order(order_id: int, db: Session = Depends(get_db)):
    """Get a lab fees order by ID"""
    order = db.query(models.LabFeesOrder).filter(models.LabFeesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/orders/", response_model=List[schemas.LabFeesOrder])
def get_lab_fees_orders(
    project_name: Optional[str] = None,
    hrs_estimation_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get all lab fees orders, optionally filtered by project name or HRS estimation ID"""
    query = db.query(models.LabFeesOrder)
    
    if project_name:
        query = query.filter(models.LabFeesOrder.project_name == project_name)
    if hrs_estimation_id:
        query = query.filter(models.LabFeesOrder.hrs_estimation_id == hrs_estimation_id)
    
    return query.order_by(models.LabFeesOrder.created_at.desc()).all()


@router.get("/labor-rates")
def get_labor_rates(db: Session = Depends(get_db)):
    """Get all labor rates for staff role selection"""
    rates = db.query(LaborRate).all()
    return [{"labor_role": r.labor_role, "hourly_rate": r.hourly_rate} for r in rates]


# Seed Data

@router.post("/seed")
def seed_data():
    """Seed the database with Lab1 data"""
    try:
        seed_lab_fees()
        return {"message": "Database seeded successfully with Lab1 data"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding database: {str(e)}")
