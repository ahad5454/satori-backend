from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --------- Line Schemas ----------
class AsbestosLineIn(BaseModel):
    component_name: str
    unit_label: str
    actuals: float = 0.0
    bulks_per_unit: float = 0.0

class LeadLineIn(BaseModel):
    component_name: str
    xrf_shots: float = 0.0
    chips_wipes: float = 0.0

class MoldLineIn(BaseModel):
    component_name: str
    tape_lift: float = 0.0
    spore_trap: float = 0.0
    culturable: float = 0.0

class ORMIn(BaseModel):
    building_total_sf: Optional[float] = None
    hours: float = 0.0


# --------- Create Payload ----------
class HRSEstimationCreate(BaseModel):
    project_name: Optional[str] = None

    # Optional overrides
    override_minutes_asbestos: Optional[float] = None
    override_minutes_xrf: Optional[float] = None
    override_minutes_lead: Optional[float] = None
    override_minutes_mold: Optional[float] = None

    field_staff_count: int = Field(default=1, ge=1)
    efficiency_factor: Optional[float] = None

    asbestos_lines: List[AsbestosLineIn] = []
    lead_lines: List[LeadLineIn] = []
    mold_lines: List[MoldLineIn] = []
    orm: Optional[ORMIn] = None

    # NEW FIELDS
    selected_role: Optional[str] = None  # "Env Scientist" or "Env Technician"
    manual_labor_hours: Optional[Dict[str, float]] = None  # {"Program Manager": 5, "Accounting": 2}


# --------- Response Schemas ----------
class AsbestosLine(BaseModel):
    id: int
    component_name: str
    unit_label: str
    actuals: float
    bulks_per_unit: float
    bulk_summary: float
    class Config: orm_mode = True

class LeadLine(BaseModel):
    id: int
    component_name: str
    xrf_shots: float
    chips_wipes: float
    class Config: orm_mode = True

class MoldLine(BaseModel):
    id: int
    component_name: str
    tape_lift: float
    spore_trap: float
    culturable: float
    class Config: orm_mode = True

class ORM(BaseModel):
    id: int
    building_total_sf: Optional[float]
    hours: float
    class Config: orm_mode = True


class HRSEstimation(BaseModel):
    id: int
    project_name: Optional[str]

    default_minutes_asbestos: float
    default_minutes_xrf: float
    default_minutes_lead: float
    default_minutes_mold: float

    override_minutes_asbestos: Optional[float]
    override_minutes_xrf: Optional[float]
    override_minutes_lead: Optional[float]
    override_minutes_mold: Optional[float]

    field_staff_count: int
    efficiency_factor: float

    total_plm: float
    total_xrf_shots: float
    total_chips_wipes: float
    total_tape_lift: float
    total_spore_trap: float
    total_culturable: float
    orm_hours: float

    suggested_hours_base: float
    suggested_hours_final: float
    labor_breakdown: Optional[Dict[str, Any]] = None

    # NEW ROLE/COST FIELDS
    selected_role: Optional[str] = None
    calculated_cost: Optional[float] = None
    manual_labor_hours: Optional[Dict[str, float]] = None
    manual_labor_costs: Optional[Dict[str, float]] = None
    total_cost: Optional[float] = None

    asbestos_lines: List[AsbestosLine]
    lead_lines: List[LeadLine]
    mold_lines: List[MoldLine]
    orm_record: Optional[ORM]

    class Config:
        orm_mode = True
