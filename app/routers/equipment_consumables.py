from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas
from app.utils.project_summary import save_or_update_module_summary
from app.utils.estimate_snapshot import save_module_to_snapshot

router = APIRouter()

# Categories

@router.get("/categories/", response_model=List[schemas.EquipmentCategory])
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.EquipmentCategory).all()

@router.post("/categories/", response_model=schemas.EquipmentCategory)
def create_category(category: schemas.EquipmentCategoryCreate, db: Session = Depends(get_db)):
    new_category = models.EquipmentCategory(
        name=category.name,
        section=category.section
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@router.put("/categories/{category_id}", response_model=schemas.EquipmentCategory)
def update_category(category_id: int, category: schemas.EquipmentCategoryUpdate, db: Session = Depends(get_db)):
    db_cat = db.query(models.EquipmentCategory).filter(models.EquipmentCategory.id == category_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.name is not None:
        db_cat.name = category.name
    if category.section is not None:
        db_cat.section = category.section
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    db_cat = db.query(models.EquipmentCategory).filter(models.EquipmentCategory.id == category_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(db_cat)
    db.commit()
    return None

# Items

@router.get("/items/", response_model=List[schemas.EquipmentItem])
def get_items(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.EquipmentItem)
    if category_id:
        query = query.filter(models.EquipmentItem.category_id == category_id)
    return query.all()

@router.post("/items/", response_model=schemas.EquipmentItem)
def create_item(item: schemas.EquipmentItemCreate, db: Session = Depends(get_db)):
    db_cat = db.query(models.EquipmentCategory).filter(models.EquipmentCategory.id == item.category_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    new_item = models.EquipmentItem(
        category_id=item.category_id,
        description=item.description,
        unit=item.unit,
        unit_cost=item.unit_cost
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@router.put("/items/{item_id}", response_model=schemas.EquipmentItem)
def update_item(item_id: int, item: schemas.EquipmentItemUpdate, db: Session = Depends(get_db)):
    db_item = db.query(models.EquipmentItem).filter(models.EquipmentItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.description is not None:
        db_item.description = item.description
    if item.unit is not None:
        db_item.unit = item.unit
    if item.unit_cost is not None:
        db_item.unit_cost = item.unit_cost
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.EquipmentItem).filter(models.EquipmentItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return None

# Orders / Estimates

@router.post("/orders/", response_model=schemas.EquipmentOrder)
def create_order(order: schemas.EquipmentOrderCreate, db: Session = Depends(get_db)):
    new_order = models.EquipmentOrder(
        project_name=order.project_name,
        section_1_total=order.section_1_total,
        section_2_total=order.section_2_total,
        total_cost=order.total_cost,
        order_details=order.order_details
    )
    db.add(new_order)
    db.flush()
    
    # Save project estimate summary
    save_or_update_module_summary(
        db=db,
        project_name=order.project_name,
        module_name="equipment",
        estimate_total=order.total_cost,
        estimate_breakdown={
            "section_1_total": order.section_1_total,
            "section_2_total": order.section_2_total,
            "order_details": order.order_details
        }
    )
    
    # Save snapshot
    try:
        inputs_dict = order.model_dump() if hasattr(order, 'model_dump') else order.dict()
    except:
        inputs_dict = order.dict() if hasattr(order, 'dict') else {}
        
    outputs_dict = {
        "id": new_order.id,
        "project_name": new_order.project_name,
        "section_1_total": new_order.section_1_total,
        "section_2_total": new_order.section_2_total,
        "total_cost": new_order.total_cost,
        "order_details": new_order.order_details
    }
    
    save_module_to_snapshot(
        db=db,
        project_name=order.project_name,
        module_name="equipment",
        inputs=inputs_dict,
        outputs=outputs_dict
    )
    
    db.commit()
    db.refresh(new_order)
    return new_order

@router.get("/orders/{project_name}", response_model=List[schemas.EquipmentOrder])
def get_orders(project_name: str, db: Session = Depends(get_db)):
    return db.query(models.EquipmentOrder).filter(models.EquipmentOrder.project_name == project_name).order_by(models.EquipmentOrder.created_at.desc()).all()
