from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.seed.seed_hrs_estimator import seed_hrs_estimator
from app.models.lab_fees import ServiceCategory, Test, TurnTime, Rate

router = APIRouter()

# internal helpers 
DEFAULTS = {
    "asbestos": 15.0,  # 2002
    "xrf": 3.0,        # 3300
    "lead": 10.0,      # 2003 (chips/wipes)
    "mold": 20.0       # 2004
}


HRS_TO_LAB_MAPPING = {
    "asbestos": {
        "service_category": "PLM - Bulk Building Materials",
        "test_name": "EPA/600/R-93/116 (<1%)",
        "turnaround": "24 hr" 
    },
    "lead_xrf": {
        "service_category": "",
        "test_name": "",
        "turnaround": ""
    },
    "lead_chips_wipes": {
        "service_category": "Lead Laboratory Services",
        "test_name": "Paint Chips (SW-846-7000B)",
        "turnaround": "24 hr" 
    },
    "mold_tape_lift": {
        "service_category": "Mold Related Services - EMLab P&K",
        "test_name": "Direct Microscopic Examination",
        "turnaround": "Standard"
    },
    "mold_spore_trap": {
        "service_category": "Mold Related Services - EMLab P&K",
        "test_name": "Spore Trap Analysis",
        "turnaround": "Standard"
    },
    "mold_culturable": {
        "service_category": "Mold Related Services - EMLab P&K",
        "test_name": "Culturable air fungi speciation",
        "turnaround": "Standard"
    }
}



def update_lab_fees_from_hrs(db: Session, hrs_estimation: models.HRSEstimation):
    mapping_values = {
        "asbestos": hrs_estimation.total_plm,
        "lead_xrf": hrs_estimation.total_xrf_shots,
        "lead_chips_wipes": hrs_estimation.total_chips_wipes,
        "mold_tape_lift": hrs_estimation.total_tape_lift,
        "mold_spore_trap": hrs_estimation.total_spore_trap,
        "mold_culturable": hrs_estimation.total_culturable,
    }

    updated = []
    for key, meta in HRS_TO_LAB_MAPPING.items():
        total_value = mapping_values.get(key, 0.0)
        if total_value == 0:
            continue

        print(f"🔍 Checking mapping for {key}: {meta}")

        service = db.query(ServiceCategory).filter(ServiceCategory.name == meta["service_category"]).first()
        if not service:
            print(f"❌ Service category not found: {meta['service_category']}")
            continue

        test = db.query(Test).filter(Test.name == meta["test_name"], Test.service_category_id == service.id).first()
        if not test:
            print(f"❌ Test not found: {meta['test_name']} (service_category_id={service.id})")
            continue

        turn = db.query(TurnTime).filter(TurnTime.label == meta["turnaround"]).first()
        if not turn:
            print(f"❌ Turnaround not found: {meta['turnaround']}")
            continue

        rate = db.query(Rate).filter(
            Rate.test_id == test.id,
            Rate.turn_time_id == turn.id
        ).first()

        if not rate:
            print(f"❌ Rate not found for test_id={test.id}, turn_time_id={turn.id}")
            continue

        print(f"✅ Updating {meta['test_name']} → sample_count={total_value}")
        rate.sample_count = total_value
        updated.append({
            "service_category": meta["service_category"],
            "test": meta["test_name"],
            "turnaround": meta["turnaround"],
            "sample_count": total_value
        })

    if updated:
        db.commit()
        print("🔄 Lab Fees updated from HRS Estimator:", updated)
    else:
        print("⚠️ No Lab Fees records were updated. Check mapping values above.")


def derive_efficiency_factor(staff_count: int) -> float:
    # 1 sampler -> 1.0 ; 2 samplers -> 0.7 ; >=3 -> 0.6
    if staff_count <= 1:
        return 1.0
    if staff_count == 2:
        return 0.7
    return 0.6


@router.post("/estimate", response_model=schemas.HRSEstimation)
def create_estimate(payload: schemas.HRSEstimationCreate, db: Session = Depends(get_db)):
    # Prepare estimation header
    eff = payload.efficiency_factor if payload.efficiency_factor is not None else derive_efficiency_factor(payload.field_staff_count)

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
    db.flush()  # get est.id for child rows

    # Asbestos lines 
    total_plm = 0.0
    for line in payload.asbestos_lines:
        bulk_summary = (line.actuals or 0.0) * (line.bulks_per_unit or 0.0)
        total_plm += bulk_summary
        db.add(models.AsbestosComponentLine(
            estimation_id=est.id,
            component_name=line.component_name,
            unit_label=line.unit_label,
            actuals=line.actuals or 0.0,
            bulks_per_unit=line.bulks_per_unit or 0.0,
            bulk_summary=bulk_summary
        ))

    # Lead lines 
    total_xrf = 0.0
    total_chips = 0.0
    for line in payload.lead_lines:
        x = line.xrf_shots or 0.0
        c = line.chips_wipes or 0.0
        total_xrf += x
        total_chips += c
        db.add(models.LeadComponentLine(
            estimation_id=est.id,
            component_name=line.component_name,
            xrf_shots=x,
            chips_wipes=c
        ))

    # Mold lines 
    total_tape = 0.0
    total_spore = 0.0
    total_cult = 0.0
    for line in payload.mold_lines:
        t = line.tape_lift or 0.0
        s = line.spore_trap or 0.0
        cu = line.culturable or 0.0
        total_tape += t
        total_spore += s
        total_cult += cu
        db.add(models.MoldComponentLine(
            estimation_id=est.id,
            component_name=line.component_name,
            tape_lift=t,
            spore_trap=s,
            culturable=cu
        ))

    # ORM 
    orm_hours = 0.0
    if payload.orm is not None:
        orm_hours = payload.orm.hours or 0.0
        db.add(models.OtherRegulatedMaterials(
            estimation_id=est.id,
            building_total_sf=payload.orm.building_total_sf,
            hours=orm_hours
        ))

    # Persist totals to header 
    est.total_plm = total_plm
    est.total_xrf_shots = total_xrf
    est.total_chips_wipes = total_chips
    est.total_tape_lift = total_tape
    est.total_spore_trap = total_spore
    est.total_culturable = total_cult
    est.orm_hours = orm_hours

    # Minutes per sample: use override if present else default 
    m_asb = est.override_minutes_asbestos if est.override_minutes_asbestos is not None else est.default_minutes_asbestos
    m_xrf = est.override_minutes_xrf if est.override_minutes_xrf is not None else est.default_minutes_xrf
    m_lead = est.override_minutes_lead if est.override_minutes_lead is not None else est.default_minutes_lead
    m_mold = est.override_minutes_mold if est.override_minutes_mold is not None else est.default_minutes_mold

    # Hours (base) before staffing efficiency 
    h_asb = (m_asb * total_plm) / 60.0
    h_xrf = (m_xrf * total_xrf) / 60.0
    h_lead = (m_lead * total_chips) / 60.0
    mold_samples_total = total_tape + total_spore + total_cult
    h_mold = (m_mold * mold_samples_total) / 60.0
    h_orm = orm_hours

    suggested_base = h_asb + h_xrf + h_lead + h_mold + h_orm

    # Apply staffing factor ONLY to field sampling portions (asbestos/lead/xrf/mold)
    field_hours_base = h_asb + h_xrf + h_lead + h_mold
    field_hours_adj = field_hours_base * est.efficiency_factor
    est.suggested_hours_base = round(suggested_base, 2)
    est.suggested_hours_final = round(field_hours_adj + h_orm, 2)

    # Base labor breakdown (hours)
    est.labor_breakdown = {
        "asbestos_hours": round(h_asb, 2),
        "lead_xrf_hours": round(h_xrf, 2),
        "lead_chips_wipes_hours": round(h_lead, 2),
        "mold_hours": round(h_mold, 2),
        "orm_hours": round(h_orm, 2),
        "field_staff_count": est.field_staff_count,
        "efficiency_factor": est.efficiency_factor
    }

    # COST CALCULATIONS (New)
    selected_role = payload.selected_role
    manual_hours = payload.manual_labor_hours or {}

    selected_rate = None
    calculated_cost = None
    manual_costs = {}
    total_manual_cost = 0.0

    # Fetch rate for selected role
    if selected_role:
        rate_entry = db.query(models.LaborRate).filter(models.LaborRate.labor_role == selected_role).first()
        if not rate_entry:
            raise HTTPException(status_code=400, detail=f"Invalid selected_role: {selected_role}")
        selected_rate = rate_entry.hourly_rate
        calculated_cost = round(est.suggested_hours_final * selected_rate, 2)

    # Manual labor costs
    for role, hours in manual_hours.items():
        rate_entry = db.query(models.LaborRate).filter(models.LaborRate.labor_role == role).first()
        if not rate_entry:
            continue
        role_cost = round(hours * rate_entry.hourly_rate, 2)
        manual_costs[role] = role_cost
        total_manual_cost += role_cost

    total_cost = (calculated_cost or 0.0) + total_manual_cost

    est.selected_role = selected_role
    est.calculated_cost = calculated_cost
    est.manual_labor_hours = manual_hours
    est.manual_labor_costs = manual_costs
    est.total_cost = round(total_cost, 2)

    db.commit()
    db.refresh(est)

    # Update Lab Fees (Rate.sample_count) based on HRS estimation totals   
    update_lab_fees_from_hrs(db, est)

    return est


@router.get("/estimate/{estimation_id}", response_model=schemas.HRSEstimation)
def get_estimate(estimation_id: int, db: Session = Depends(get_db)):
    est = db.query(models.HRSEstimation).filter(models.HRSEstimation.id == estimation_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estimation not found")
    return est


@router.get("/estimates", response_model=List[schemas.HRSEstimation])
def list_estimates(db: Session = Depends(get_db)):
    return db.query(models.HRSEstimation).order_by(models.HRSEstimation.id.desc()).all()


@router.post("/seed", tags=["HRS Estimator"])
def seed():
    try:
        return seed_hrs_estimator()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
