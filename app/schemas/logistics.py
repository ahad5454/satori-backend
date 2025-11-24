from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


# ---------- Input Schemas for Each Block ----------

class DailyDrivingIn(BaseModel):
    project_location: Optional[str] = None
    num_vehicles: int = Field(default=1, ge=0)
    one_way_miles: float = 0.0
    drive_time_hours: float = 0.0  # one-way drive time
    project_duration_days: int = Field(default=0, ge=0)

    # Older design style inputs
    mpg: Optional[float] = None
    cost_per_gallon: Optional[float] = None

    # Newer design: cost/fee per mile, based on vehicle type
    cost_per_mile: Optional[float] = None


class FlightsIn(BaseModel):
    project_location: Optional[str] = None
    num_tickets: int = Field(default=0, ge=0)
    roundtrip_cost_per_ticket: float = 0.0

    # One-way flight time in hours (we'll apply "×2 + 1.5" internally)
    flight_time_hours_one_way: float = 0.0

    layover_city: Optional[str] = None
    has_overnight: bool = False
    layover_hotel_name: Optional[str] = None
    layover_cost_per_night: Optional[float] = None
    layover_rooms: Optional[int] = None


class RentalIn(BaseModel):
    project_location: Optional[str] = None
    num_vehicles: int = Field(default=0, ge=0)

    # "C" or "T" (car or truck) - stored for reference only
    vehicle_category: Optional[str] = None

    # Rental quote snapshot
    daily_rate: Optional[float] = None
    weekly_rate: Optional[float] = None
    monthly_rate: Optional[float] = None

    # "daily", "weekly", or "monthly"
    rental_period_type: Optional[str] = None
    rental_days: int = Field(default=0, ge=0)

    # Lump-sum fuel allowance/estimate for the rental
    fuel_cost_estimate: Optional[float] = None


class LodgingIn(BaseModel):
    project_location: Optional[str] = None
    hotel_name: Optional[str] = None
    night_cost_with_taxes: float = 0.0
    project_duration_days: int = Field(default=0, ge=0)

    # For this design: single occupancy always ⇒ one room per staff
    num_staff: int = Field(default=0, ge=0)


# ---------- Create Payload ----------

class LogisticsEstimationCreate(BaseModel):
    project_name: Optional[str] = None

    # "driving" or "flight" (no strict enum enforced, but UI should restrict)
    site_access_mode: str = Field(default="driving")

    is_local_project: bool = False
    use_client_vehicle: bool = False

    # Professional labor role used to price travel / driving time
    professional_role: Optional[str] = None

    # How many staff are traveling / staying
    num_staff: int = Field(default=0, ge=0)

    # Per diem per person per night (only applied when hotel is used)
    per_diem_rate: float = 0.0

    driving: Optional[DailyDrivingIn] = None
    flights: Optional[FlightsIn] = None
    rental: Optional[RentalIn] = None
    lodging: Optional[LodgingIn] = None


# ---------- Response Schema ----------

class LogisticsEstimation(BaseModel):
    id: int

    project_name: Optional[str]

    site_access_mode: str
    is_local_project: bool
    use_client_vehicle: bool

    professional_role: Optional[str]
    num_staff: int
    per_diem_rate: float

    # Raw input snapshots
    driving_input: Optional[Dict[str, Any]] = None
    flights_input: Optional[Dict[str, Any]] = None
    rental_input: Optional[Dict[str, Any]] = None
    lodging_input: Optional[Dict[str, Any]] = None

    # Driving totals
    total_driving_miles: float
    total_driving_fuel_cost: float
    total_driving_labor_hours: float
    total_driving_labor_cost: float
    total_driving_cost: float

    # Flight totals
    total_flight_ticket_cost: float
    total_flight_labor_hours: float
    total_flight_labor_cost: float
    total_layover_room_cost: float
    total_flight_cost: float

    # Rental totals
    total_rental_base_cost: float
    total_rental_fuel_cost: float
    total_rental_cost: float

    # Lodging / per diem
    total_lodging_room_cost: float
    total_per_diem_cost: float

    # Grand total
    total_logistics_cost: float

    class Config:
        orm_mode = True
