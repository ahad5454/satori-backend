from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class RoundtripDrivingIn(BaseModel):
    project_location: Optional[str] = None
    num_vehicles: int = Field(default=1, ge=0)
    one_way_miles: float = 0.0

    drive_time_hours: Optional[float] = None
    project_duration_days: int = Field(default=1, ge=1)

    mpg: Optional[float] = None
    cost_per_gallon: Optional[float] = None
    cost_per_mile: Optional[float] = None

    anchorage_flat_fee: Optional[float] = None


class DailyDrivingIn(BaseModel):
    site_location: Optional[str] = None
    lodging_location: Optional[str] = None

    daily_miles: float = 0.0
    daily_drive_time_hours: Optional[float] = None

    project_duration_days: int = Field(default=1, ge=1)

    mpg: Optional[float] = None
    cost_per_gallon: Optional[float] = None
    cost_per_mile: Optional[float] = None


class FlightsIn(BaseModel):
    project_location: Optional[str] = None
    num_tickets: int = Field(default=0, ge=0)
    roundtrip_cost_per_ticket: float = 0.0
    flight_time_hours_one_way: float = 0.0

    layover_city: Optional[str] = None
    has_overnight: bool = False
    layover_hotel_name: Optional[str] = None
    layover_cost_per_night: Optional[float] = None
    layover_rooms: Optional[int] = None


class RentalIn(BaseModel):
    project_location: Optional[str] = None
    num_vehicles: int = Field(default=0, ge=0)

    vehicle_category: Optional[str] = None
    daily_rate: Optional[float] = None
    weekly_rate: Optional[float] = None
    monthly_rate: Optional[float] = None
    rental_period_type: Optional[str] = None
    rental_days: int = Field(default=0, ge=0)
    fuel_cost_estimate: Optional[float] = None


class LodgingIn(BaseModel):
    project_location: Optional[str] = None
    hotel_name: Optional[str] = None
    night_cost_with_taxes: float = 0.0
    project_duration_days: int = 0
    num_staff: int = Field(default=0, ge=0)


class StaffLineIn(BaseModel):
    role: str
    count: int = Field(default=1, ge=0)


class LogisticsEstimationCreate(BaseModel):
    project_name: Optional[str] = None
    site_access_mode: str = "driving"

    is_local_project: bool = False
    use_client_vehicle: bool = False

    professional_role: Optional[str] = None
    num_staff: int = 0
    staff: Optional[List[StaffLineIn]] = None

    rate_multiplier: float = 1.0
    per_diem_rate: float = 0.0

    roundtrip_driving: Optional[RoundtripDrivingIn] = None
    daily_driving: Optional[DailyDrivingIn] = None
    flights: Optional[FlightsIn] = None
    rental: Optional[RentalIn] = None
    lodging: Optional[LodgingIn] = None


class LogisticsEstimation(BaseModel):
    id: int
    project_name: Optional[str]

    site_access_mode: str
    is_local_project: bool
    use_client_vehicle: bool

    professional_role: Optional[str]
    num_staff: int

    staff_breakdown: Optional[List[Dict[str, Any]]] = None
    staff_labor_costs: Optional[Dict[str, float]] = None
    total_staff_count: int
    rate_multiplier: float

    per_diem_rate: float

    driving_input: Optional[Dict[str, Any]] = None
    flights_input: Optional[Dict[str, Any]] = None
    rental_input: Optional[Dict[str, Any]] = None
    lodging_input: Optional[Dict[str, Any]] = None

    # Driving totals
    roundtrip_driving_miles: float
    daily_driving_miles: float
    total_driving_miles: float

    roundtrip_driving_labor_hours: float
    daily_driving_labor_hours: float
    total_driving_labor_hours: float

    total_driving_fuel_cost: float
    total_driving_labor_cost: float
    total_driving_cost: float

    # Flights
    total_flight_ticket_cost: float
    total_flight_labor_hours: float
    total_flight_labor_cost: float
    total_layover_room_cost: float
    total_flight_cost: float

    # Rental
    total_rental_base_cost: float
    total_rental_fuel_cost: float
    total_rental_cost: float

    # Lodging / Per Diem
    total_lodging_room_cost: float
    total_per_diem_cost: float

    # Grand Total
    total_logistics_cost: float

    class Config:
        orm_mode = True
