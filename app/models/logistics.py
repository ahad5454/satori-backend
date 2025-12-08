from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON
from datetime import datetime
from app.database import Base


class LogisticsEstimation(Base):
    __tablename__ = "logistics_estimations"

    id = Column(Integer, primary_key=True, index=True)

    # Basic context
    project_name = Column(String, nullable=True)

    # "driving" or "flight" as primary site access mode
    site_access_mode = Column(String, nullable=False, default="driving")

    # Local vs non-local logic
    is_local_project = Column(Boolean, nullable=False, default=False)

    # Rare exception: client provides their own vehicle even if flights exist
    use_client_vehicle = Column(Boolean, nullable=False, default=False)

    # Legacy single-role fields
    professional_role = Column(String, nullable=True)
    num_staff = Column(Integer, nullable=False, default=0)

    # Staff breakdown — list of {"role": str, "count": int}
    staff_breakdown = Column(JSON, nullable=True)

    # Per-role labor cost summary
    staff_labor_costs = Column(JSON, nullable=True)

    # Total staff count
    total_staff_count = Column(Integer, nullable=False, default=0)

    # Global labor rate multiplier (0.50, 0.75, 1.0)
    rate_multiplier = Column(Float, nullable=False, default=1.0)

    # Per diem per person per night
    per_diem_rate = Column(Float, nullable=False, default=0.0)

    # Raw input snapshots
    driving_input = Column(JSON, nullable=True)   # {"roundtrip": {...}, "daily": {...}}
    flights_input = Column(JSON, nullable=True)
    rental_input = Column(JSON, nullable=True)
    lodging_input = Column(JSON, nullable=True)

    # Driving Totals
    # Distances
    roundtrip_driving_miles = Column(Float, nullable=False, default=0.0)
    daily_driving_miles = Column(Float, nullable=False, default=0.0)
    total_driving_miles = Column(Float, nullable=False, default=0.0)

    # Labor hours
    roundtrip_driving_labor_hours = Column(Float, nullable=False, default=0.0)
    daily_driving_labor_hours = Column(Float, nullable=False, default=0.0)
    total_driving_labor_hours = Column(Float, nullable=False, default=0.0)

    # Costs
    total_driving_fuel_cost = Column(Float, nullable=False, default=0.0)
    total_driving_labor_cost = Column(Float, nullable=False, default=0.0)
    total_driving_cost = Column(Float, nullable=False, default=0.0)

    # Flights 
    total_flight_ticket_cost = Column(Float, nullable=False, default=0.0)
    total_flight_labor_hours = Column(Float, nullable=False, default=0.0)
    total_flight_labor_cost = Column(Float, nullable=False, default=0.0)
    total_layover_room_cost = Column(Float, nullable=False, default=0.0)
    total_flight_cost = Column(Float, nullable=False, default=0.0)

    # Rentals
    total_rental_base_cost = Column(Float, nullable=False, default=0.0)
    total_rental_fuel_cost = Column(Float, nullable=False, default=0.0)
    total_rental_cost = Column(Float, nullable=False, default=0.0)

    # Lodging + Per Diem
    total_lodging_room_cost = Column(Float, nullable=False, default=0.0)
    total_per_diem_cost = Column(Float, nullable=False, default=0.0)

    # Grand Total
    total_logistics_cost = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
