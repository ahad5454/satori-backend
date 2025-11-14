from sqlalchemy import inspect, text
from app.database import engine, SessionLocal
from app.models.hrs_estimator import SamplingDefault, ComponentList, LaborRate


def ensure_hrs_estimator_columns():
    """Add missing columns to hrs_estimations table safely."""
    inspector = inspect(engine)
    
    # Check if table exists
    if not inspector.has_table("hrs_estimations"):
        return  # Table doesn't exist yet, will be created by Base.metadata.create_all()
    
    columns = [col["name"] for col in inspector.get_columns("hrs_estimations")]

    with engine.begin() as conn:
        if "selected_role" not in columns:
            conn.execute(text("ALTER TABLE hrs_estimations ADD COLUMN selected_role VARCHAR(255);"))
        if "calculated_cost" not in columns:
            conn.execute(text("ALTER TABLE hrs_estimations ADD COLUMN calculated_cost FLOAT;"))
        if "manual_labor_hours" not in columns:
            conn.execute(text("ALTER TABLE hrs_estimations ADD COLUMN manual_labor_hours JSON;"))
        if "manual_labor_costs" not in columns:
            conn.execute(text("ALTER TABLE hrs_estimations ADD COLUMN manual_labor_costs JSON;"))
        if "total_cost" not in columns:
            conn.execute(text("ALTER TABLE hrs_estimations ADD COLUMN total_cost FLOAT;"))


def seed_hrs_estimator():
    ensure_hrs_estimator_columns()  # Ensure schema is up-to-date

    db = SessionLocal()

    # --- Sampling Default Minutes ---
    sampling_defaults = [
        ("asbestos", 15.0),
        ("xrf", 3.0),
        ("lead", 10.0),
        ("mold", 20.0)
    ]

    for sampling_type, minutes in sampling_defaults:
        if not db.query(SamplingDefault).filter_by(sampling_type=sampling_type).first():
            db.add(SamplingDefault(sampling_type=sampling_type, minutes_per_sample=minutes))

    # --- Component Lists ---
    asbestos_components = [
        "GWB/JC", "Flooring", "Ceilings", "Exterior Sides (CAB, etc.)", "Piping", "Tanks"
    ]
    lead_components = ["Walls", "Windows", "Doors", "Exterior", "Other"]
    mold_components = ["Living Room", "Kitchen", "Bath", "Crawl Space", "Mech Room", "Bedroom"]

    for c in asbestos_components:
        if not db.query(ComponentList).filter_by(category="asbestos", component_name=c).first():
            db.add(ComponentList(category="asbestos", component_name=c))
    for c in lead_components:
        if not db.query(ComponentList).filter_by(category="lead", component_name=c).first():
            db.add(ComponentList(category="lead", component_name=c))
    for c in mold_components:
        if not db.query(ComponentList).filter_by(category="mold", component_name=c).first():
            db.add(ComponentList(category="mold", component_name=c))

    # --- Labor Rates ---
    labor_rates = [
        ("Program Manager", 131.55),
        ("Project Manager", 104.23),
        ("Env Scientist", 93.17),
        ("Env Technician", 72.40),
        ("Accounting", 95.36),
        ("Administrative", 54.80)
    ]

    for role, rate in labor_rates:
        if not db.query(LaborRate).filter_by(labor_role=role).first():
            db.add(LaborRate(labor_role=role, hourly_rate=rate))

    db.commit()
    db.close()

    return {"message": "HRS Estimator reference data seeded successfully."}
