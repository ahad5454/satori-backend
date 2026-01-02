from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.seed.seed_hrs_estimator import seed_hrs_estimator
from app.models.lab_fees import ServiceCategory, Test, TurnTime, Rate
from app.utils.project_summary import save_or_update_module_summary
from app.utils.estimate_snapshot import save_module_to_snapshot

router = APIRouter()

# internal helpers
DEFAULTS = {
    "asbestos": 15.0,
    "xrf": 3.0,
    "lead": 10.0,
    "mold": 20.0
}

"""
HRS to Lab Fees mapping - Data Contract

This mapping defines how HRS Sample Estimator outputs map to Lab Fees test selections.
Each mapping entry explicitly defines:
- hrs_output_key: The HRS output field name (e.g., "total_plm")
- service_category: The Lab Fees service category name
- test_name: The Lab Fees test name
- turnaround: The turnaround time label

This is a data contract, not a naming convention. The hrs_output_key is explicitly
defined to avoid brittle assumptions about key names.

The frontend uses this mapping to automatically derive Lab Fees quantities from HRS outputs.
Future mappings added here will work automatically without code changes.
"""
HRS_TO_LAB_MAPPING = {
    "asbestos": {
        "hrs_output_key": "total_plm",
        "service_category": "PLM - Bulk Building Materials",
        "test_name": "EPA/600/R-93/116 (<1%)",
        "turnaround": "24 hr"
    },
    "lead_xrf": {
        "hrs_output_key": "total_xrf_shots",
        "service_category": "",
        "test_name": "",
        "turnaround": ""
    },
    "lead_chips_wipes": {
        "hrs_output_key": "total_chips_wipes",
        "service_category": "Lead Laboratory Services",
        "test_name": "Paint Chips (SW-846-7000B)",
        "turnaround": "24 hr"
    },
    "mold_tape_lift": {
        "hrs_output_key": "total_tape_lift",
        "service_category": "Mold Related Services - EMLab P&K",
        "test_name": "Direct Microscopic Examination",
        "turnaround": "Standard"
    },
    "mold_spore_trap": {
        "hrs_output_key": "total_spore_trap",
        "service_category": "Mold Related Services - EMLab P&K",
        "test_name": "Spore Trap Analysis",
        "turnaround": "Standard"
    },
    "mold_culturable": {
        "hrs_output_key": "total_culturable",
        "service_category": "Mold Related Services - EMLab P&K",
        "test_name": "Culturable air fungi speciation",
        "turnaround": "Standard"
    }
}


def derive_efficiency_factor(staff_count: int) -> float:
    if staff_count <= 1:
        return 1.0
    if staff_count == 2:
        return 0.7
    return 0.6


@router.post("/estimate", response_model=schemas.HRSEstimation)
def create_estimate(payload: schemas.HRSEstimationCreate, db: Session = Depends(get_db)):

    eff = payload.efficiency_factor if payload.efficiency_factor is not None else derive_efficiency_factor(
        payload.field_staff_count
    )

    est = models.HRSEstimation(
        project_name=payload.project_name,
        default_minutes_asbestos=DEFAULTS["asbestos"],
        default_minutes_xrf=DEFAULTS["xrf"],
        default_minutes_lead=DEFAULTS["lead"],
        default_minutes_mold=DEFAULTS["mold"],
        override_minutes_asbestos=payload.override_minutes_asbestos,
        override_minutes_xrf=payload.override_minutes_xrf,
        override_minutes_lead=payload.override_minutes_lead,
        override_minutes_mold=payload.override_minutes_mold,
        field_staff_count=payload.field_staff_count,
        efficiency_factor=eff,
    )

    db.add(est)
    db.flush()

    # -------------------------
    # SAMPLE TOTALS
    # -------------------------
    total_plm = total_xrf = total_chips = total_tape = total_spore = total_cult = 0.0

    for l in payload.asbestos_lines:
        bulk = (l.actuals or 0) * (l.bulks_per_unit or 0)
        total_plm += bulk
        db.add(models.AsbestosComponentLine(
            estimation_id=est.id,
            component_name=l.component_name,
            unit_label=l.unit_label,
            actuals=l.actuals or 0,
            bulks_per_unit=l.bulks_per_unit or 0,
            bulk_summary=bulk
        ))

    for l in payload.lead_lines:
        total_xrf += l.xrf_shots or 0
        total_chips += l.chips_wipes or 0
        db.add(models.LeadComponentLine(
            estimation_id=est.id,
            component_name=l.component_name,
            xrf_shots=l.xrf_shots or 0,
            chips_wipes=l.chips_wipes or 0
        ))

    for l in payload.mold_lines:
        total_tape += l.tape_lift or 0
        total_spore += l.spore_trap or 0
        total_cult += l.culturable or 0
        db.add(models.MoldComponentLine(
            estimation_id=est.id,
            component_name=l.component_name,
            tape_lift=l.tape_lift or 0,
            spore_trap=l.spore_trap or 0,
            culturable=l.culturable or 0
        ))

    orm_hours = payload.orm.hours if payload.orm else 0.0

    est.total_plm = total_plm
    est.total_xrf_shots = total_xrf
    est.total_chips_wipes = total_chips
    est.total_tape_lift = total_tape
    est.total_spore_trap = total_spore
    est.total_culturable = total_cult
    est.orm_hours = orm_hours

    # -------------------------
    # HOURS CALCULATION
    # -------------------------
    h_asb = (DEFAULTS["asbestos"] * total_plm) / 60
    h_xrf = (DEFAULTS["xrf"] * total_xrf) / 60
    h_lead = (DEFAULTS["lead"] * total_chips) / 60
    h_mold = (DEFAULTS["mold"] * (total_tape + total_spore + total_cult)) / 60

    field_hours = h_asb + h_xrf + h_lead + h_mold
    est.suggested_hours_base = round(field_hours + orm_hours, 2)
    est.suggested_hours_final = round((field_hours * eff) + orm_hours, 2)

    # -------------------------
    # NORMALIZE STAFF INPUT
    # -------------------------
    staff_array = payload.staff if payload.staff and len(payload.staff) > 0 else None
    selected_role = payload.selected_role

    if est.suggested_hours_final > 0 and not staff_array and not selected_role:
        raise HTTPException(
            status_code=400,
            detail="At least one labor role must be selected to calculate labor cost."
        )

    # -------------------------
    # COST CALCULATION
    # -------------------------
    staff_labor_costs = {}
    staff_labor_hours = {}
    staff_breakdown = []
    total_staff_cost = 0.0

    if staff_array:
        for s in staff_array:
            role = s.get("role")
            count = s.get("count", 0)

            if not role or count <= 0:
                continue

            rate = db.query(models.LaborRate).filter(
                models.LaborRate.labor_role == role
            ).first()

            if not rate:
                raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

            hours = round(est.suggested_hours_final, 2)
            cost = round(hours * rate.hourly_rate * count, 2)

            staff_labor_hours[role] = hours
            staff_labor_costs[role] = cost
            staff_breakdown.append({"role": role, "count": count})
            total_staff_cost += cost

        est.staff_breakdown = staff_breakdown
        est.staff_labor_hours = staff_labor_hours
        est.staff_labor_costs = staff_labor_costs
        est.calculated_cost = total_staff_cost

    elif selected_role:
        rate = db.query(models.LaborRate).filter(
            models.LaborRate.labor_role == selected_role
        ).first()

        if not rate:
            raise HTTPException(status_code=400, detail="Invalid selected role")

        est.calculated_cost = round(est.suggested_hours_final * rate.hourly_rate, 2)
        est.selected_role = selected_role

    est.total_cost = est.calculated_cost or 0.0

    db.commit()
    db.refresh(est)
    
    # Save/update project estimate summary
    # Note: This happens after commit to ensure the estimate is persisted
    save_or_update_module_summary(
        db=db,
        project_name=payload.project_name,
        module_name="hrs_estimator",
        estimate_total=est.total_cost or 0.0,
        estimate_breakdown={
            "calculated_cost": est.calculated_cost,
            "suggested_hours_final": est.suggested_hours_final,
            "staff_breakdown": est.staff_breakdown,
            "staff_labor_costs": est.staff_labor_costs
        }
    )
    
    # Save to estimate snapshot (full inputs + outputs for form rehydration)
    # Convert payload to dict for JSON storage
    try:
        inputs_dict = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
    except:
        inputs_dict = payload.dict() if hasattr(payload, 'dict') else {}
    
    outputs_dict = {
        "id": est.id,
        "project_name": est.project_name,
        "total_cost": est.total_cost,
        "calculated_cost": est.calculated_cost,
        "suggested_hours_final": est.suggested_hours_final,
        "staff_breakdown": est.staff_breakdown,
        "staff_labor_costs": est.staff_labor_costs,
        "staff_labor_hours": est.staff_labor_hours,
        "selected_role": est.selected_role,
        "field_staff_count": est.field_staff_count,
        "efficiency_factor": est.efficiency_factor,
        "total_plm": est.total_plm,
        "total_xrf_shots": est.total_xrf_shots,
        "total_chips_wipes": est.total_chips_wipes,
        "total_tape_lift": est.total_tape_lift,
        "total_spore_trap": est.total_spore_trap,
        "total_culturable": est.total_culturable,
        "orm_hours": est.orm_hours,
    }
    save_module_to_snapshot(
        db=db,
        project_name=payload.project_name,
        module_name="hrs_estimator",
        inputs=inputs_dict,
        outputs=outputs_dict
    )
    
    db.commit()
    
    return est


@router.get("/estimate/{estimation_id}", response_model=schemas.HRSEstimation)
def get_estimate(estimation_id: int, db: Session = Depends(get_db)):
    est = db.query(models.HRSEstimation).filter(models.HRSEstimation.id == estimation_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estimation not found")
    return est

@router.get("/labor-rates")
def get_labor_rates(db: Session = Depends(get_db)):
    """
    Fetch all labor roles and hourly rates for HRS Estimator staff selection.
    """
    rates = db.query(models.LaborRate).all()
    return [
        {
            "labor_role": r.labor_role,
            "hourly_rate": r.hourly_rate
        }
        for r in rates
    ]
