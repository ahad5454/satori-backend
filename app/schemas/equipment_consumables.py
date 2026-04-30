from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class EquipmentItemBase(BaseModel):
    description: str
    unit: str
    unit_cost: float

class EquipmentItemCreate(EquipmentItemBase):
    category_id: int

class EquipmentItemUpdate(BaseModel):
    description: Optional[str] = None
    unit: Optional[str] = None
    unit_cost: Optional[float] = None

class EquipmentItem(EquipmentItemBase):
    id: int
    category_id: int

    class Config:
        from_attributes = True

class EquipmentCategoryBase(BaseModel):
    name: str
    section: int

class EquipmentCategoryCreate(EquipmentCategoryBase):
    pass

class EquipmentCategoryUpdate(BaseModel):
    name: Optional[str] = None
    section: Optional[int] = None

class EquipmentCategory(EquipmentCategoryBase):
    id: int
    items: List[EquipmentItem] = []

    class Config:
        from_attributes = True

class EquipmentOrderBase(BaseModel):
    project_name: Optional[str] = None
    section_1_total: float
    section_2_total: float
    total_cost: float
    order_details: Dict[str, Any]

class EquipmentOrderCreate(EquipmentOrderBase):
    pass

class EquipmentOrder(EquipmentOrderBase):
    id: int

    class Config:
        from_attributes = True
