from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import math

from app.database import get_db
from app import models, schemas

router = APIRouter(
    tags=["Logistics"]
)


def _get_labor_rate(db: Session, professional_role: str) -> float:
    """
    Fetch hourly labor rate from the shared HRS LaborRate table.
    Returns None if not found.
    """
    if not professional_role:
        return None

    rate_entry = db.query(models.LaborRate).filter(
        models.LaborRate.labor_role == professional_role
    ).first()

    if not rate_entry:
        return None

    return rate_entry.hourly_rate


@router.post("/estimate", response_model=schemas.LogisticsEstimation)
def create_logistics_estimate(
    payload: schemas.LogisticsEstimationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new LogisticsEstimation record and compute all cost components:
    - Daily site driving
    - Flights (tickets + travel labor + layover rooms)
    - Rental vehicles
    - Lodging + per diem
    """
    # Prepare header
    est = models.LogisticsEstimation(
        project_name=payload.project_name,
        site_access_mode=payload.site_access_mode or "driving",
        is_local_project=payload.is_local_project,
        use_client_vehicle=payload.use_client_vehicle,
        professional_role=payload.professional_role,
        num_staff=payload.num_staff or 0,
        per_diem_rate=payload.per_diem_rate or 0.0,
    )

    db.add(est)
    db.flush()  # get est.id if needed later

    labor_rate = _get_labor_rate(db, payload.professional_role) if payload.professional_role else None

    # ------------- DAILY SITE DRIVING -------------
    total_driving_cost = 0.0
    if payload.driving:
        d = payload.driving
        est.driving_input = d.dict()

        days = max(d.project_duration_days or 0, 0)
        one_way_miles = max(d.one_way_miles or 0.0, 0.0)
        num_staff = max(payload.num_staff or 0, 0)

        total_miles = one_way_miles * 2 * days
        est.total_driving_miles = total_miles

        # New design first: cost_per_mile (if provided)
        driving_fuel_cost = 0.0
        if d.cost_per_mile is not None:
            driving_fuel_cost = total_miles * max(d.cost_per_mile, 0.0)
        else:
            # Fallback to older MPG / cost-per-gallon model
            if d.mpg and d.cost_per_gallon:
                gallons = total_miles / d.mpg if d.mpg > 0 else 0.0
                driving_fuel_cost = gallons * max(d.cost_per_gallon, 0.0)

        est.total_driving_fuel_cost = round(driving_fuel_cost, 2)

        # Driving labor: daily round-trip time × days × num_staff
        drive_time_hours = max(d.drive_time_hours or 0.0, 0.0)
        total_drive_hours = drive_time_hours * 2 * days * num_staff
        est.total_driving_labor_hours = round(total_drive_hours, 2)

        driving_labor_cost = 0.0
        if labor_rate is not None and total_drive_hours > 0:
            driving_labor_cost = total_drive_hours * labor_rate

        est.total_driving_labor_cost = round(driving_labor_cost, 2)
        total_driving_cost = driving_fuel_cost + driving_labor_cost
        est.total_driving_cost = round(total_driving_cost, 2)
    else:
        # Ensure defaults are clean even if no driving block is sent
        est.total_driving_miles = 0.0
        est.total_driving_fuel_cost = 0.0
        est.total_driving_labor_hours = 0.0
        est.total_driving_labor_cost = 0.0
        est.total_driving_cost = 0.0

    # ------------- FLIGHTS -------------
    total_flight_cost = 0.0
    if payload.site_access_mode == "flight" and payload.flights and not payload.is_local_project:
        f = payload.flights
        est.flights_input = f.dict()

        num_tickets = max(f.num_tickets or 0, 0)
        ticket_price = max(f.roundtrip_cost_per_ticket or 0.0, 0.0)

        ticket_cost = num_tickets * ticket_price
        est.total_flight_ticket_cost = round(ticket_cost, 2)

        # Travel labor: (one-way time × 2 + 1.5 hours buffer) × number of tickets
        one_way_time = max(f.flight_time_hours_one_way or 0.0, 0.0)
        travel_time_per_person = (one_way_time * 2.0) + 1.5
        total_travel_hours = travel_time_per_person * num_tickets
        est.total_flight_labor_hours = round(total_travel_hours, 2)

        travel_labor_cost = 0.0
        if labor_rate is not None and total_travel_hours > 0:
            travel_labor_cost = total_travel_hours * labor_rate

        est.total_flight_labor_cost = round(travel_labor_cost, 2)

        # Layover hotel cost (only if overnight is required)
        layover_cost = 0.0
        if f.has_overnight and f.layover_cost_per_night and f.layover_rooms:
            layover_cost = max(f.layover_cost_per_night, 0.0) * max(f.layover_rooms, 0)
        est.total_layover_room_cost = round(layover_cost, 2)

        total_flight_cost = ticket_cost + travel_labor_cost + layover_cost
        est.total_flight_cost = round(total_flight_cost, 2)
    else:
        est.total_flight_ticket_cost = 0.0
        est.total_flight_labor_hours = 0.0
        est.total_flight_labor_cost = 0.0
        est.total_layover_room_cost = 0.0
        est.total_flight_cost = 0.0

    # ------------- RENTAL VEHICLES -------------
    total_rental_cost = 0.0
    # Rule: flights → rental car, unless use_client_vehicle=True
    if (
        payload.site_access_mode == "flight"
        and not payload.is_local_project
        and not payload.use_client_vehicle
        and payload.rental
    ):
        r = payload.rental
        est.rental_input = r.dict()

        rental_days = max(r.rental_days or 0, 0)
        base_cost = 0.0

        if r.rental_period_type == "daily" and r.daily_rate is not None:
            base_cost = rental_days * max(r.daily_rate, 0.0)
        elif r.rental_period_type == "weekly" and r.weekly_rate is not None:
            weeks = math.ceil(rental_days / 7) if rental_days > 0 else 0
            base_cost = weeks * max(r.weekly_rate, 0.0)
        elif r.rental_period_type == "monthly" and r.monthly_rate is not None:
            months = math.ceil(rental_days / 30) if rental_days > 0 else 0
            base_cost = months * max(r.monthly_rate, 0.0)

        fuel_cost = max(r.fuel_cost_estimate or 0.0, 0.0)

        est.total_rental_base_cost = round(base_cost, 2)
        est.total_rental_fuel_cost = round(fuel_cost, 2)

        total_rental_cost = base_cost + fuel_cost
        est.total_rental_cost = round(total_rental_cost, 2)
    else:
        est.total_rental_base_cost = 0.0
        est.total_rental_fuel_cost = 0.0
        est.total_rental_cost = 0.0

    # ------------- LODGING + PER DIEM -------------
    total_room_cost = 0.0
    total_per_diem = 0.0

    if not payload.is_local_project and payload.lodging:
        l = payload.lodging
        est.lodging_input = l.dict()

        days = max(l.project_duration_days or 0, 0)
        # Single occupancy: one room per staff
        staff_for_lodging = max(l.num_staff or payload.num_staff or 0, 0)

        night_cost = max(l.night_cost_with_taxes or 0.0, 0.0)
        total_room_cost = staff_for_lodging * night_cost * days

        per_diem_rate = max(payload.per_diem_rate or 0.0, 0.0)
        # Per diem only when there is hotel involvement
        if staff_for_lodging > 0 and days > 0:
            total_per_diem = per_diem_rate * staff_for_lodging * days

    est.total_lodging_room_cost = round(total_room_cost, 2)
    est.total_per_diem_cost = round(total_per_diem, 2)

    # ------------- GRAND TOTAL -------------
    est.total_logistics_cost = round(
        est.total_driving_cost
        + est.total_flight_cost
        + est.total_rental_cost
        + est.total_lodging_room_cost
        + est.total_per_diem_cost,
        2,
    )

    db.commit()
    db.refresh(est)

    return est


@router.get("/estimate/{estimation_id}", response_model=schemas.LogisticsEstimation)
def get_logistics_estimate(estimation_id: int, db: Session = Depends(get_db)):
    est = db.query(models.LogisticsEstimation).filter(
        models.LogisticsEstimation.id == estimation_id
    ).first()
    if not est:
        raise HTTPException(status_code=404, detail="Logistics estimation not found")
    return est


@router.get("/estimates", response_model=List[schemas.LogisticsEstimation])
def list_logistics_estimates(db: Session = Depends(get_db)):
    return (
        db.query(models.LogisticsEstimation)
        .order_by(models.LogisticsEstimation.id.desc())
        .all()
    )


@router.get("/labor-rates")
def get_labor_rates(db: Session = Depends(get_db)):
    """
    Fetch all labor rates from the HRS LaborRate table for use in professional role selection.
    """
    rates = db.query(models.LaborRate).all()
    return [{"labor_role": rate.labor_role, "hourly_rate": rate.hourly_rate} for rate in rates]
