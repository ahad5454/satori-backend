from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class LaboratoryBase(BaseModel):
    name: str
    address: Optional[str] = None
    contact_info: Optional[str] = None


class LaboratoryCreate(LaboratoryBase):
    pass


class Laboratory(LaboratoryBase):
    id: int
    class Config:
        from_attributes = True


class TurnTimeBase(BaseModel):
    label: str
    hours: Optional[int] = None


class TurnTimeCreate(TurnTimeBase):
    pass


class TurnTime(TurnTimeBase):
    id: int
    class Config:
        from_attributes = True


class RateBase(BaseModel):
    test_id: int
    turn_time_id: int
    lab_id: int
    price: float
    sample_count: Optional[float] = None  


class RateCreate(RateBase):
    pass


class Rate(RateBase):
    id: int
    turn_time: Optional[TurnTime] = None
    class Config:
        from_attributes = True


class TestBase(BaseModel):
    name: str
    service_category_id: int


class TestCreate(TestBase):
    pass


class Test(TestBase):
    id: int
    rates: Optional[List[Rate]] = []
    class Config:
        from_attributes = True


class ServiceCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    lab_id: int


class ServiceCategoryCreate(ServiceCategoryBase):
    pass


class ServiceCategory(ServiceCategoryBase):
    id: int
    tests: Optional[List[Test]] = []
    class Config:
        from_attributes = True


# Lab Fees Staff Assignment Schemas
class LabFeesStaffAssignmentBase(BaseModel):
    role: str
    count: int = 1
    hours_per_person: float = 0.0


class LabFeesStaffAssignmentCreate(LabFeesStaffAssignmentBase):
    pass


class LabFeesStaffAssignment(LabFeesStaffAssignmentBase):
    id: int
    order_id: int
    total_hours: float
    hourly_rate: float
    total_cost: float
    created_at: datetime
    
    class Config:
        from_attributes = True


# Lab Fees Order Schemas
class LabFeesOrderBase(BaseModel):
    project_name: Optional[str] = None
    hrs_estimation_id: Optional[int] = None
    order_details: Optional[Dict[str, Any]] = None


class LabFeesOrderCreate(LabFeesOrderBase):
    staff_assignments: Optional[List[LabFeesStaffAssignmentCreate]] = []


class LabFeesOrder(LabFeesOrderBase):
    id: int
    total_samples: float
    total_lab_fees_cost: float
    total_staff_labor_cost: float
    total_cost: float
    staff_breakdown: Optional[List[Dict[str, Any]]] = None
    staff_labor_costs: Optional[Dict[str, float]] = None
    staff_assignments: Optional[List[LabFeesStaffAssignment]] = []
    created_at: datetime
    
    class Config:
        from_attributes = True
