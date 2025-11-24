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

    # Professional role used for travel/drive labor (Env Sci / Env Tech, etc.)
    professional_role = Column(String, nullable=True)

    # How many staff are traveling / staying
    num_staff = Column(Integer, nullable=False, default=0)

    # Per diem per person per day (snapshot at time of estimate)
    per_diem_rate = Column(Float, nullable=False, default=0.0)

    # Raw input snapshots (so UI/layout can evolve without changing DB)
    driving_input = Column(JSON, nullable=True)   # Daily site driving block
    flights_input = Column(JSON, nullable=True)   # Flights block
    rental_input = Column(JSON, nullable=True)    # Rental car/truck block
    lodging_input = Column(JSON, nullable=True)   # Lodging block

    # ---- Derived Driving Totals ----
    total_driving_miles = Column(Float, nullable=False, default=0.0)
    total_driving_fuel_cost = Column(Float, nullable=False, default=0.0)
    total_driving_labor_hours = Column(Float, nullable=False, default=0.0)
    total_driving_labor_cost = Column(Float, nullable=False, default=0.0)
    total_driving_cost = Column(Float, nullable=False, default=0.0)  # fuel/mileage + labor

    # ---- Derived Flight Totals ----
    total_flight_ticket_cost = Column(Float, nullable=False, default=0.0)
    total_flight_labor_hours = Column(Float, nullable=False, default=0.0)
    total_flight_labor_cost = Column(Float, nullable=False, default=0.0)
    total_layover_room_cost = Column(Float, nullable=False, default=0.0)
    total_flight_cost = Column(Float, nullable=False, default=0.0)  # tickets + labor + layover

    # ---- Derived Rental Totals ----
    total_rental_base_cost = Column(Float, nullable=False, default=0.0)
    total_rental_fuel_cost = Column(Float, nullable=False, default=0.0)
    total_rental_cost = Column(Float, nullable=False, default=0.0)

    # ---- Derived Lodging / Per Diem Totals ----
    total_lodging_room_cost = Column(Float, nullable=False, default=0.0)
    total_per_diem_cost = Column(Float, nullable=False, default=0.0)

    # ---- Grand Total ----
    total_logistics_cost = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
