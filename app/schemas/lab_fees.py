from pydantic import BaseModel
from typing import Optional, List


# -------------------------------------------------------------------
# Laboratory Schemas
# -------------------------------------------------------------------
class LaboratoryBase(BaseModel):
    name: str
    address: Optional[str] = None
    contact_info: Optional[str] = None


class LaboratoryCreate(LaboratoryBase):
    pass


class Laboratory(LaboratoryBase):
    id: int
    class Config:
        orm_mode = True


# -------------------------------------------------------------------
# Turnaround Time Schemas
# -------------------------------------------------------------------
class TurnTimeBase(BaseModel):
    label: str
    hours: Optional[int] = None


class TurnTimeCreate(TurnTimeBase):
    pass


class TurnTime(TurnTimeBase):
    id: int
    class Config:
        orm_mode = True


# -------------------------------------------------------------------
# Rate Schemas
# -------------------------------------------------------------------
class RateBase(BaseModel):
    test_id: int
    turn_time_id: int
    lab_id: int
    price: float
    sample_count: Optional[float] = None   # ✅ New field added


class RateCreate(RateBase):
    pass


class Rate(RateBase):
    id: int
    turn_time: Optional[TurnTime] = None
    class Config:
        orm_mode = True


# -------------------------------------------------------------------
# Test Schemas
# -------------------------------------------------------------------
class TestBase(BaseModel):
    name: str
    service_category_id: int


class TestCreate(TestBase):
    pass


class Test(TestBase):
    id: int
    rates: Optional[List[Rate]] = []
    class Config:
        orm_mode = True


# -------------------------------------------------------------------
# Service Category Schemas
# -------------------------------------------------------------------
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
        orm_mode = True
