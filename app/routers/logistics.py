from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
import math

from app.database import get_db
from app import models, schemas

router = APIRouter(
    tags=["Logistics"]
)

# Default Anchorage flat fee per day (can be overridden via payload)
DEFAULT_ANCHORAGE_FEE_PER_DAY = 45.0

# Default speed for auto-calculated drive times (MPH)
DEFAULT_DRIVING_SPEED_MPH = 55.0


def _get_labor_rate(db: Session, professional_role: str) -> Optional[float]:
    """
    Fetch hourly labor rate from the shared HRS LaborRate table.
    Returns None if not found.
    """
    if not professional_role:
        return None

    rate_entry = (
        db.query(models.LaborRate)
        .filter(models.LaborRate.labor_role == professional_role)
        .first()
    )
    if not rate_entry:
        return None
    return rate_entry.hourly_rate


def _is_anchorage(location: Optional[str]) -> bool:
    if not location:
        return False
    return location.strip().lower() == "anchorage"


@router.post("/estimate", response_model=schemas.LogisticsEstimation)
def create_logistics_estimate(
    payload: schemas.LogisticsEstimationCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new LogisticsEstimation record and compute all cost components:

    - Roundtrip driving (home/office <-> project site)
    - Daily driving (lodging <-> site commute)
    - Flights (tickets + travel labor + layover rooms)
    - Rental vehicles
    - Lodging + per diem

    Supports new payload field `staff: [{role, count}]`.
    Falls back to legacy `professional_role` + `num_staff` if `staff` is not provided.
    """

    # -------- Staff normalization (multi-role) --------
    staff_list: List[Dict[str, Any]] = []
    if payload.staff:
        for s in payload.staff:
            cnt = int(s.count or 0)
            if cnt > 0:
                staff_list.append({"role": s.role, "count": cnt})
    else:
        # Backwards compatibility: use professional_role + num_staff
        if payload.professional_role and payload.num_staff and payload.num_staff > 0:
            staff_list.append(
                {"role": payload.professional_role, "count": int(payload.num_staff)}
            )

    total_staff = sum(s["count"] for s in staff_list) if staff_list else 0

    # Guard multiplier (never <= 0)
    rate_multiplier = (
        payload.rate_multiplier if payload.rate_multiplier and payload.rate_multiplier > 0 else 1.0
    )

    # -------- Create header row --------
    est = models.LogisticsEstimation(
        project_name=payload.project_name,
        site_access_mode=payload.site_access_mode or "driving",
        is_local_project=payload.is_local_project,
        use_client_vehicle=payload.use_client_vehicle,
        professional_role=payload.professional_role,
        num_staff=payload.num_staff or 0,
        staff_breakdown=staff_list or None,
        staff_labor_costs={},  # will populate later
        total_staff_count=total_staff,
        rate_multiplier=rate_multiplier,
        per_diem_rate=payload.per_diem_rate or 0.0,
    )

    db.add(est)
    db.flush()  # get est.id if needed later

    # We accumulate per-role staff costs across driving + flights.
    staff_costs: Dict[str, float] = {}
    staff_hours: Dict[str, float] = {}

    def _rate_for_role(role_name: str) -> float:
        r = _get_labor_rate(db, role_name)
        return r if r is not None else 0.0

    # ------------------------------------------------------------------
    # DRIVING (Option A: Roundtrip + Daily)
    # ------------------------------------------------------------------
    anchorage_driving = False  # True if roundtrip location is Anchorage
    roundtrip_days = 0

    driving_snapshot: Dict[str, Any] = {"roundtrip": None, "daily": None}

    # ---- Roundtrip Driving ----
    roundtrip_miles = 0.0
    roundtrip_labor_hours_total = 0.0
    roundtrip_labor_cost_total = 0.0
    roundtrip_vehicle_cost = 0.0

    if payload.site_access_mode == "driving" and payload.roundtrip_driving:
        rt = payload.roundtrip_driving
        driving_snapshot["roundtrip"] = rt.dict()

        roundtrip_days = max(rt.project_duration_days or 1, 1)
        one_way_miles = max(rt.one_way_miles or 0.0, 0.0)
        roundtrip_miles_per_day = one_way_miles * 2.0
        roundtrip_miles = roundtrip_miles_per_day * roundtrip_days

        anchorage_driving = _is_anchorage(rt.project_location)

        # Vehicle cost:
        if anchorage_driving:
            # Anchorage => flat fee per day, ignores cost-per-mile
            flat_fee = (
                rt.anchorage_flat_fee
                if rt.anchorage_flat_fee is not None
                else DEFAULT_ANCHORAGE_FEE_PER_DAY
            )
            roundtrip_vehicle_cost = flat_fee * roundtrip_days
        else:
            # Non-Anchorage => cost per mile or MPG fallback
            if rt.cost_per_mile is not None:
                roundtrip_vehicle_cost = roundtrip_miles * max(rt.cost_per_mile, 0.0)
            else:
                if rt.mpg and rt.cost_per_gallon:
                    gallons = roundtrip_miles / rt.mpg if rt.mpg > 0 else 0.0
                    roundtrip_vehicle_cost = gallons * max(rt.cost_per_gallon, 0.0)

        # Labor hours: auto-calc if time not provided
        drive_time_hours_one_way = rt.drive_time_hours
        if (drive_time_hours_one_way is None or drive_time_hours_one_way <= 0) and roundtrip_miles_per_day > 0:
            total_roundtrip_hours_per_day = roundtrip_miles_per_day / DEFAULT_DRIVING_SPEED_MPH
            drive_time_hours_one_way = total_roundtrip_hours_per_day / 2.0

        drive_time_hours_one_way = max(drive_time_hours_one_way or 0.0, 0.0)
        drive_hours_per_person_roundtrip = drive_time_hours_one_way * 2.0 * roundtrip_days

        if staff_list:
            for s in staff_list:
                role = s["role"]
                count = s["count"]
                role_hours = drive_hours_per_person_roundtrip * count
                rate = _rate_for_role(role)
                role_cost = round(role_hours * rate * rate_multiplier, 2)

                staff_hours[role] = staff_hours.get(role, 0.0) + round(role_hours, 2)
                staff_costs[role] = staff_costs.get(role, 0.0) + role_cost

                roundtrip_labor_hours_total += role_hours
                roundtrip_labor_cost_total += role_cost
        else:
            # Legacy single-role behavior
            count = max(payload.num_staff or 0, 0)
            total_hours = drive_hours_per_person_roundtrip * count
            rate = _rate_for_role(payload.professional_role) if payload.professional_role else 0.0
            total_cost = total_hours * rate * rate_multiplier

            roundtrip_labor_hours_total = total_hours
            roundtrip_labor_cost_total = total_cost

            if payload.professional_role:
                role = payload.professional_role
                staff_hours[role] = staff_hours.get(role, 0.0) + round(total_hours, 2)
                staff_costs[role] = staff_costs.get(role, 0.0) + round(total_cost, 2)

    # ---- Daily Driving ----
    daily_miles_total = 0.0
    daily_labor_hours_total = 0.0
    daily_labor_cost_total = 0.0
    daily_vehicle_cost = 0.0

    if payload.daily_driving:
        dd = payload.daily_driving
        driving_snapshot["daily"] = dd.dict()

        daily_days = max(dd.project_duration_days or roundtrip_days or 1, 1)
        daily_miles_per_day = max(dd.daily_miles or 0.0, 0.0)
        daily_miles_total = daily_miles_per_day * daily_days

        # Anchorage rule: flat fee replaces vehicle mileage for Anchorage.
        daily_location_is_anchorage = _is_anchorage(dd.site_location)
        if not anchorage_driving and not daily_location_is_anchorage:
            if dd.cost_per_mile is not None:
                daily_vehicle_cost = daily_miles_total * max(dd.cost_per_mile, 0.0)
            else:
                if dd.mpg and dd.cost_per_gallon:
                    gallons = daily_miles_total / dd.mpg if dd.mpg > 0 else 0.0
                    daily_vehicle_cost = gallons * max(dd.cost_per_gallon, 0.0)
        # else → Anchorage daily miles have vehicle cost covered by flat fee

        # Labor hours: auto-calc if not provided
        daily_time_hours_one_way = dd.daily_drive_time_hours
        if (daily_time_hours_one_way is None or daily_time_hours_one_way <= 0) and daily_miles_per_day > 0:
            total_daily_roundtrip_hours = daily_miles_per_day / DEFAULT_DRIVING_SPEED_MPH
            daily_time_hours_one_way = total_daily_roundtrip_hours / 2.0

        daily_time_hours_one_way = max(daily_time_hours_one_way or 0.0, 0.0)
        daily_hours_per_person = daily_time_hours_one_way * 2.0 * daily_days

        if staff_list:
            for s in staff_list:
                role = s["role"]
                count = s["count"]
                role_daily_hours = daily_hours_per_person * count
                rate = _rate_for_role(role)
                role_daily_cost = round(role_daily_hours * rate * rate_multiplier, 2)

                staff_hours[role] = staff_hours.get(role, 0.0) + round(role_daily_hours, 2)
                staff_costs[role] = staff_costs.get(role, 0.0) + role_daily_cost

                daily_labor_hours_total += role_daily_hours
                daily_labor_cost_total += role_daily_cost
        else:
            count = max(payload.num_staff or 0, 0)
            total_daily_hours = daily_hours_per_person * count
            rate = _rate_for_role(payload.professional_role) if payload.professional_role else 0.0
            total_daily_cost = total_daily_hours * rate * rate_multiplier

            daily_labor_hours_total = total_daily_hours
            daily_labor_cost_total = total_daily_cost

            if payload.professional_role:
                role = payload.professional_role
                staff_hours[role] = staff_hours.get(role, 0.0) + round(total_daily_hours, 2)
                staff_costs[role] = staff_costs.get(role, 0.0) + round(total_daily_cost, 2)

    # ---- Aggregate Driving Totals ----
    est.driving_input = (
        driving_snapshot
        if (driving_snapshot.get("roundtrip") or driving_snapshot.get("daily"))
        else None
    )

    est.roundtrip_driving_miles = round(roundtrip_miles, 2)
    est.daily_driving_miles = round(daily_miles_total, 2)
    est.total_driving_miles = round(roundtrip_miles + daily_miles_total, 2)

    est.roundtrip_driving_labor_hours = round(roundtrip_labor_hours_total, 2)
    est.daily_driving_labor_hours = round(daily_labor_hours_total, 2)
    est.total_driving_labor_hours = round(
        roundtrip_labor_hours_total + daily_labor_hours_total, 2
    )

    est.total_driving_fuel_cost = round(roundtrip_vehicle_cost + daily_vehicle_cost, 2)
    est.total_driving_labor_cost = round(
        roundtrip_labor_cost_total + daily_labor_cost_total, 2
    )
    est.total_driving_cost = round(
        est.total_driving_fuel_cost + est.total_driving_labor_cost, 2
    )

    # ------------------------------------------------------------------
    # FLIGHTS
    # ------------------------------------------------------------------
    total_flight_cost = 0.0
    total_flight_labor_hours = 0.0
    total_flight_labor_cost = 0.0

    if payload.site_access_mode == "flight" and payload.flights and not payload.is_local_project:
        f = payload.flights
        est.flights_input = f.dict()

        num_tickets = max(f.num_tickets or 0, 0)
        ticket_price = max(f.roundtrip_cost_per_ticket or 0.0, 0.0)

        ticket_cost = num_tickets * ticket_price
        est.total_flight_ticket_cost = round(ticket_cost, 2)

        one_way_time = max(f.flight_time_hours_one_way or 0.0, 0.0)
        travel_time_per_person = (one_way_time * 2.0) + 1.5

        if staff_list:
            for s in staff_list:
                role = s["role"]
                count = s["count"]
                role_travel_hours = travel_time_per_person * count
                rate = _rate_for_role(role)
                role_travel_cost = round(role_travel_hours * rate * rate_multiplier, 2)

                staff_hours[role] = staff_hours.get(role, 0.0) + round(role_travel_hours, 2)
                staff_costs[role] = staff_costs.get(role, 0.0) + role_travel_cost

                total_flight_labor_hours += role_travel_hours
                total_flight_labor_cost += role_travel_cost
        else:
            role = payload.professional_role
            count = max(payload.num_staff or 0, 0)
            total_travel_hours = travel_time_per_person * count
            rate = _rate_for_role(role)
            total_flight_labor_hours = total_travel_hours
            total_flight_labor_cost = total_travel_hours * rate * rate_multiplier

            if role:
                staff_hours[role] = staff_hours.get(role, 0.0) + round(total_travel_hours, 2)
                staff_costs[role] = staff_costs.get(role, 0.0) + round(total_flight_labor_cost, 2)

        est.total_flight_labor_hours = round(total_flight_labor_hours, 2)
        est.total_flight_labor_cost = round(total_flight_labor_cost, 2)

        layover_cost = 0.0
        if f.has_overnight and f.layover_cost_per_night and f.layover_rooms:
            layover_cost = max(f.layover_cost_per_night, 0.0) * max(f.layover_rooms, 0)
        est.total_layover_room_cost = round(layover_cost, 2)

        total_flight_cost = ticket_cost + total_flight_labor_cost + layover_cost
        est.total_flight_cost = round(total_flight_cost, 2)
    else:
        est.total_flight_ticket_cost = 0.0
        est.total_flight_labor_hours = 0.0
        est.total_flight_labor_cost = 0.0
        est.total_layover_room_cost = 0.0
        est.total_flight_cost = 0.0

    # ------------------------------------------------------------------
    # RENTAL VEHICLES
    # ------------------------------------------------------------------
    total_rental_cost = 0.0
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

    # ------------------------------------------------------------------
    # LODGING + PER DIEM
    # ------------------------------------------------------------------
    total_room_cost = 0.0
    total_per_diem = 0.0

    if not payload.is_local_project and payload.lodging:
        l = payload.lodging
        est.lodging_input = l.dict()

        days = max(l.project_duration_days or 0, 0)

        if staff_list:
            staff_for_lodging = sum(s["count"] for s in staff_list)
        else:
            staff_for_lodging = max(l.num_staff or payload.num_staff or 0, 0)

        night_cost = max(l.night_cost_with_taxes or 0.0, 0.0)
        total_room_cost = staff_for_lodging * night_cost * days

        per_diem_rate = max(payload.per_diem_rate or 0.0, 0.0)
        if staff_for_lodging > 0 and days > 0:
            total_per_diem = per_diem_rate * staff_for_lodging * days

    est.total_lodging_room_cost = round(total_room_cost, 2)
    est.total_per_diem_cost = round(total_per_diem, 2)

    # ------------------------------------------------------------------
    # Finalize staff costs + legacy compatibility
    # ------------------------------------------------------------------
    est.staff_labor_costs = staff_costs if staff_costs else None
    est.total_staff_count = total_staff

    est.num_staff = payload.num_staff or total_staff
    if not est.professional_role and staff_list and len(staff_list) == 1:
        est.professional_role = staff_list[0]["role"]

    # ------------------------------------------------------------------
    # GRAND TOTAL
    # ------------------------------------------------------------------
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
    est = (
        db.query(models.LogisticsEstimation)
        .filter(models.LogisticsEstimation.id == estimation_id)
        .first()
    )
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
    Fetch all labor rates from the HRS LaborRate table for use in staff role selection.
    """
    rates = db.query(models.LaborRate).all()
    return [{"labor_role": rate.labor_role, "hourly_rate": rate.hourly_rate} for rate in rates]
