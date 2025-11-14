from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.lab_fees import Laboratory, ServiceCategory, Test, TurnTime, Rate


def seed_lab_fees():
    db: Session = SessionLocal()

    try:
        # --- Create tables if they don't exist (never drop existing data!)
        print("Creating tables if not exist...")
        Base.metadata.create_all(bind=engine)

        # Helper: Insert or get existing record safely
        def get_or_create(model, defaults=None, **kwargs):
            instance = db.query(model).filter_by(**kwargs).first()
            if instance:
                return instance
            params = dict(**kwargs)
            if defaults:
                params.update(defaults)
            instance = model(**params)
            db.add(instance)
            try:
                db.commit()
                db.refresh(instance)
            except Exception:
                db.rollback()
                instance = db.query(model).filter_by(**kwargs).first()
            return instance

        # --- 2️⃣ Create Lab1 laboratory (safe - won't duplicate if exists)
        print("Seeding Lab1 laboratory...")
        lab1 = get_or_create(
            Laboratory,
            name="Lab1",
            defaults={
                "address": "123 Health Street, Cityville",
                "contact_info": "(021) 12345678"
            }
        )

        # Step 1: Create Turn Times
        turn_times_data = [
            ("3 hr", 3),
            ("6 hr", 6),
            ("24 hr", 24),
            ("30 hr", 30),
            ("48 hr", 48),
            ("72 hr", 72),
            ("96 hr", 96),
            ("1 Wk", 168),
            ("2 Wk", 336),
            # Mold service turnaround times
            ("Standard", 336),  # 2 weeks
            ("Next Day", 24),   # 24 hours
            ("Same day", 8),    # 8 hours
            ("Holiday Wkd", 48), # 48 hours
            # Environmental Chemistry turnaround times
            ("1 Day", 24),      # 24 hours
            ("2 Day", 48),      # 48 hours
            ("3 Day", 72),      # 72 hours
            ("4 Day", 96),      # 96 hours
        ]

        turn_times = {}
        for label, hours in turn_times_data:
            tt = get_or_create(TurnTime, label=label, hours=hours)
            turn_times[label] = tt

        # Step 2: Categories (Updated to include lab_id)
        pcm_air = get_or_create(ServiceCategory, name="PCM Air Analysis Services", lab_id=lab1.id, defaults={"description": "PCM Air category"})
        tem_air = get_or_create(ServiceCategory, name="TEM Air", lab_id=lab1.id, defaults={"description": "TEM Air category"})
        plm_bulk = get_or_create(ServiceCategory, name="PLM - Bulk Building Materials", lab_id=lab1.id, defaults={"description": "PLM Bulk category"})
        plm_nob = get_or_create(ServiceCategory, name="PLM - Bulk for Problem Matrices such as NOB's", lab_id=lab1.id, defaults={"description": "PLM NOB category"})
        tem_bulk = get_or_create(ServiceCategory, name="TEM Bulk Materials (Including NOB Samples)", lab_id=lab1.id, defaults={"description": "TEM Bulk Materials category"})
        tem_settled = get_or_create(ServiceCategory, name="TEM - Settled dust", lab_id=lab1.id, defaults={"description": "TEM Settled dust category"})
        soil_rock = get_or_create(ServiceCategory, name="Soil / Rock / Vermiculite Methods", lab_id=lab1.id, defaults={"description": "Soil Rock Vermiculite Methods category"})
        lead_lab = get_or_create(ServiceCategory, name="Lead Laboratory Services", lab_id=lab1.id, defaults={"description": "Lead Laboratory Services category"})
        lead_tclp = get_or_create(ServiceCategory, name="Lead Laboratory Services - TCLP (Flame AA)", lab_id=lab1.id, defaults={"description": "Lead Laboratory Services TCLP category"})
        mold_services = get_or_create(ServiceCategory, name="Mold Related Services - EMLab P&K", lab_id=lab1.id, defaults={"description": "Mold Related Services category"})
        env_chem = get_or_create(ServiceCategory, name="Environmental Chemistry Laboratory Services", lab_id=lab1.id, defaults={"description": "Environmental Chemistry Laboratory Services category"})
        
        # Step 3: Tests (Updated to include lab_id)
        tests_data = [
            ("NIOSH 7400", pcm_air.id),
            ("AHERA (40 CFR, Part 763)", tem_air.id),
            ("EPA Level II", tem_air.id),
            ("NIOSH 7402", tem_air.id),
            ("EPA/600/R-93/116 (<1%)", plm_bulk.id),
            ("EPA/600/R-93/116 (<0.25%) 400 PT", plm_bulk.id),
            ("EPA/600/R-93/116 (<0.1%) 1000 PT", plm_bulk.id),
            # New NOB tests
            ("PLM EPA NOB-EPA/600/R-93/116 (<0.5%) W/ Grav Reduction Prep", plm_nob.id),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.25%) 400 PT W/ Grav Reduction Prep", plm_nob.id),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.1%) 1000 PT W/ Grav Reduction Prep", plm_nob.id),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop)", plm_nob.id),
            # New TEM Bulk tests
            ("TEM EPA NOB EPA 600/R-93/116 (Add Prep fee if not already prepped via PLM NOB)", tem_bulk.id),
            ("TEM % by Mass - EPA 600/R-93/116", tem_bulk.id),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop) - TEM Bulk", tem_bulk.id),
            # New TEM Settled dust tests
            ("ASTM D-6480 Wipe", tem_settled.id),
            ("ASTM D 5755 MicroVac", tem_settled.id),
            ("TEM Qualitative Via Filtration Prep", tem_settled.id),
            # New Soil/Rock/Vermiculite tests
            ("PLM CARB 435 LVL A (0.25%)", soil_rock.id),
            ("PLM CARB 435 LVL B (0.1%)", soil_rock.id),
            ("PLM Qualitative", soil_rock.id),
            # New Lead Laboratory Services tests
            ("Paint Chips (SW-846-7000B)", lead_lab.id),
            ("Air (NIOSH 7082)", lead_lab.id),
            ("Wipes (SW-846-7000B)", lead_lab.id),
            ("Soil (SW-846-7000B)", lead_lab.id),
            ("Wastewater (SW-846-7000B)", lead_lab.id),
            # New Lead Laboratory Services - TCLP (Flame AA) tests
            ("Toxicity Characteristic Leaching Procedure", lead_tclp.id),
            # New Mold Related Services tests
            ("Spore Trap Analysis", mold_services.id),
            ("Spore Trap Analysis (Clad & Pen/Asp. Differentiation)", mold_services.id),
            ("Spore Trap analysis other particles - Supplement", mold_services.id),
            ("Culturable air fungi speciation", mold_services.id),
            ("Direct Microscopic Examination", mold_services.id),
            ("Quantitative spore count direct exam", mold_services.id),
            # New Environmental Chemistry Laboratory Services tests
            ("PCB Bulk Sample Caulking/Concrete/Paint Chips SW 846-3540C8082A", env_chem.id),
        ]

        tests = {}
        for name, category_id in tests_data:
            t = get_or_create(Test, name=name, service_category_id=category_id)
            tests[name] = t

        # Step 4: Rates (Updated to include lab_id)
        rates_data = [
            # PCM Air - NIOSH 7400
            ("NIOSH 7400", "3 hr", 26.90),
            ("NIOSH 7400", "6 hr", 18.55),
            ("NIOSH 7400", "24 hr", 18.55),
            ("NIOSH 7400", "48 hr", 15.50),
            ("NIOSH 7400", "72 hr", 14.00),
            ("NIOSH 7400", "96 hr", 12.55),
            ("NIOSH 7400", "1 Wk", 11.20),

            # TEM Air - AHERA
            ("AHERA (40 CFR, Part 763)", "3 hr", 396.00),
            ("AHERA (40 CFR, Part 763)", "6 hr", 111.00),
            ("AHERA (40 CFR, Part 763)", "24 hr", 79.00),
            ("AHERA (40 CFR, Part 763)", "48 hr", 69.00),
            ("AHERA (40 CFR, Part 763)", "72 hr", 63.00),
            ("AHERA (40 CFR, Part 763)", "96 hr", 56.00),
            ("AHERA (40 CFR, Part 763)", "1 Wk", 54.00),

            # TEM Air - EPA Level II
            ("EPA Level II", "3 hr", 396.00),
            ("EPA Level II", "6 hr", 111.00),
            ("EPA Level II", "24 hr", 79.00),
            ("EPA Level II", "48 hr", 69.00),
            ("EPA Level II", "72 hr", 63.00),
            ("EPA Level II", "96 hr", 56.00),
            ("EPA Level II", "1 Wk", 54.00),

            # TEM Air - NIOSH 7402
            ("NIOSH 7402", "3 hr", 0.00),
            ("NIOSH 7402", "6 hr", 227.00),
            ("NIOSH 7402", "24 hr", 192.00),
            ("NIOSH 7402", "48 hr", 159.00),
            ("NIOSH 7402", "72 hr", 145.00),
            ("NIOSH 7402", "96 hr", 137.00),
            ("NIOSH 7402", "1 Wk", 131.00),

            # PLM - Bulk Building Materials
            ("EPA/600/R-93/116 (<1%)", "3 hr", 38.00),
            ("EPA/600/R-93/116 (<1%)", "6 hr", 22.00),
            ("EPA/600/R-93/116 (<1%)", "24 hr", 9.20),
            ("EPA/600/R-93/116 (<1%)", "48 hr", 8.35),
            ("EPA/600/R-93/116 (<1%)", "72 hr", 8.35),
            ("EPA/600/R-93/116 (<1%)", "96 hr", 8.35),
            ("EPA/600/R-93/116 (<1%)", "1 Wk", 8.35),

            ("EPA/600/R-93/116 (<0.25%) 400 PT", "3 hr", 121.00),
            ("EPA/600/R-93/116 (<0.25%) 400 PT", "6 hr", 66.00),
            ("EPA/600/R-93/116 (<0.25%) 400 PT", "24 hr", 53.00),
            ("EPA/600/R-93/116 (<0.25%) 400 PT", "48 hr", 49.00),
            ("EPA/600/R-93/116 (<0.25%) 400 PT", "72 hr", 44.25),
            ("EPA/600/R-93/116 (<0.25%) 400 PT", "96 hr", 39.50),
            ("EPA/600/R-93/116 (<0.25%) 400 PT", "1 Wk", 36.75),

            ("EPA/600/R-93/116 (<0.1%) 1000 PT", "3 hr", 542.00),
            ("EPA/600/R-93/116 (<0.1%) 1000 PT", "6 hr", 170.00),
            ("EPA/600/R-93/116 (<0.1%) 1000 PT", "24 hr", 162.00),
            ("EPA/600/R-93/116 (<0.1%) 1000 PT", "48 hr", 140.00),
            ("EPA/600/R-93/116 (<0.1%) 1000 PT", "72 hr", 131.00),
            ("EPA/600/R-93/116 (<0.1%) 1000 PT", "96 hr", 124.00),
            ("EPA/600/R-93/116 (<0.1%) 1000 PT", "1 Wk", 114.00),

            # New NOB tests pricing
            # PLM EPA NOB-EPA/600/R-93/116 (<0.5%) W/ Grav Reduction Prep
            ("PLM EPA NOB-EPA/600/R-93/116 (<0.5%) W/ Grav Reduction Prep", "24 hr", 21.45),
            ("PLM EPA NOB-EPA/600/R-93/116 (<0.5%) W/ Grav Reduction Prep", "48 hr", 20.60),
            ("PLM EPA NOB-EPA/600/R-93/116 (<0.5%) W/ Grav Reduction Prep", "72 hr", 20.60),
            ("PLM EPA NOB-EPA/600/R-93/116 (<0.5%) W/ Grav Reduction Prep", "96 hr", 20.60),
            ("PLM EPA NOB-EPA/600/R-93/116 (<0.5%) W/ Grav Reduction Prep", "1 Wk", 20.60),
            ("PLM EPA NOB-EPA/600/R-93/116 (<0.5%) W/ Grav Reduction Prep", "2 Wk", 20.60),

            # PLM EPA NOB-EPA/600/R-93/116 (<.25%) 400 PT W/ Grav Reduction Prep
            ("PLM EPA NOB-EPA/600/R-93/116 (<.25%) 400 PT W/ Grav Reduction Prep", "24 hr", 95.00),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.25%) 400 PT W/ Grav Reduction Prep", "48 hr", 78.00),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.25%) 400 PT W/ Grav Reduction Prep", "72 hr", 69.00),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.25%) 400 PT W/ Grav Reduction Prep", "96 hr", 66.00),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.25%) 400 PT W/ Grav Reduction Prep", "1 Wk", 61.00),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.25%) 400 PT W/ Grav Reduction Prep", "2 Wk", 61.00),

            # PLM EPA NOB-EPA/600/R-93/116 (<.1%) 1000 PT W/ Grav Reduction Prep
            ("PLM EPA NOB-EPA/600/R-93/116 (<.1%) 1000 PT W/ Grav Reduction Prep", "24 hr", 226.00),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.1%) 1000 PT W/ Grav Reduction Prep", "48 hr", 200.00),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.1%) 1000 PT W/ Grav Reduction Prep", "72 hr", 178.00),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.1%) 1000 PT W/ Grav Reduction Prep", "96 hr", 163.00),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.1%) 1000 PT W/ Grav Reduction Prep", "1 Wk", 153.00),
            ("PLM EPA NOB-EPA/600/R-93/116 (<.1%) 1000 PT W/ Grav Reduction Prep", "2 Wk", 146.00),

            # EPA NOB Prep Fee for samples prepped but not samples (positive stop)
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop)", "24 hr", 11.95),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop)", "48 hr", 11.95),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop)", "72 hr", 11.95),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop)", "96 hr", 11.95),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop)", "1 Wk", 11.95),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop)", "2 Wk", 11.95),

            # New TEM Bulk tests pricing
            # TEM EPA NOB EPA 600/R-93/116 (Add Prep fee if not already prepped via PLM NOB)
            ("TEM EPA NOB EPA 600/R-93/116 (Add Prep fee if not already prepped via PLM NOB)", "24 hr", 156.00),
            ("TEM EPA NOB EPA 600/R-93/116 (Add Prep fee if not already prepped via PLM NOB)", "48 hr", 120.00),
            ("TEM EPA NOB EPA 600/R-93/116 (Add Prep fee if not already prepped via PLM NOB)", "72 hr", 95.00),
            ("TEM EPA NOB EPA 600/R-93/116 (Add Prep fee if not already prepped via PLM NOB)", "96 hr", 87.00),
            ("TEM EPA NOB EPA 600/R-93/116 (Add Prep fee if not already prepped via PLM NOB)", "1 Wk", 76.00),
            ("TEM EPA NOB EPA 600/R-93/116 (Add Prep fee if not already prepped via PLM NOB)", "2 Wk", 68.00),

            # TEM % by Mass - EPA 600/R-93/116
            ("TEM % by Mass - EPA 600/R-93/116", "24 hr", 558.00),
            ("TEM % by Mass - EPA 600/R-93/116", "48 hr", 489.00),
            ("TEM % by Mass - EPA 600/R-93/116", "72 hr", 445.00),
            ("TEM % by Mass - EPA 600/R-93/116", "96 hr", 400.00),
            ("TEM % by Mass - EPA 600/R-93/116", "1 Wk", 359.00),
            ("TEM % by Mass - EPA 600/R-93/116", "2 Wk", 323.00),

            # EPA NOB Prep Fee for samples prepped but not samples (positive stop) - TEM Bulk version
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop) - TEM Bulk", "24 hr", 11.95),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop) - TEM Bulk", "48 hr", 11.95),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop) - TEM Bulk", "72 hr", 11.95),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop) - TEM Bulk", "96 hr", 11.95),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop) - TEM Bulk", "1 Wk", 11.95),
            ("EPA NOB Prep Fee for samples prepped but not samples (positive stop) - TEM Bulk", "2 Wk", 11.95),

            # New TEM Settled dust tests pricing
            # ASTM D-6480 Wipe (no 3hr pricing)
            ("ASTM D-6480 Wipe", "6 hr", 483.00),
            ("ASTM D-6480 Wipe", "24 hr", 207.00),
            ("ASTM D-6480 Wipe", "48 hr", 169.00),
            ("ASTM D-6480 Wipe", "72 hr", 157.00),
            ("ASTM D-6480 Wipe", "96 hr", 144.00),
            ("ASTM D-6480 Wipe", "1 Wk", 132.00),

            # ASTM D 5755 MicroVac (no 3hr pricing)
            ("ASTM D 5755 MicroVac", "6 hr", 531.00),
            ("ASTM D 5755 MicroVac", "24 hr", 227.00),
            ("ASTM D 5755 MicroVac", "48 hr", 187.00),
            ("ASTM D 5755 MicroVac", "72 hr", 172.00),
            ("ASTM D 5755 MicroVac", "96 hr", 159.00),
            ("ASTM D 5755 MicroVac", "1 Wk", 145.00),

            # TEM Qualitative Via Filtration Prep (no 3hr pricing, "Call" for 6hr)
            ("TEM Qualitative Via Filtration Prep", "24 hr", 170.00),
            ("TEM Qualitative Via Filtration Prep", "48 hr", 135.00),
            ("TEM Qualitative Via Filtration Prep", "72 hr", 110.00),
            ("TEM Qualitative Via Filtration Prep", "96 hr", 99.00),
            ("TEM Qualitative Via Filtration Prep", "1 Wk", 91.00),

            # New Soil/Rock/Vermiculite tests pricing
            # PLM CARB 435 LVL A (0.25%)
            ("PLM CARB 435 LVL A (0.25%)", "3 hr", 506.00),
            ("PLM CARB 435 LVL A (0.25%)", "6 hr", 391.00),
            ("PLM CARB 435 LVL A (0.25%)", "24 hr", 277.00),
            ("PLM CARB 435 LVL A (0.25%)", "48 hr", 243.00),
            ("PLM CARB 435 LVL A (0.25%)", "72 hr", 202.00),
            ("PLM CARB 435 LVL A (0.25%)", "96 hr", 181.00),
            ("PLM CARB 435 LVL A (0.25%)", "1 Wk", 153.00),

            # PLM CARB 435 LVL B (0.1%)
            ("PLM CARB 435 LVL B (0.1%)", "3 hr", 703.00),
            ("PLM CARB 435 LVL B (0.1%)", "6 hr", 550.00),
            ("PLM CARB 435 LVL B (0.1%)", "24 hr", 359.00),
            ("PLM CARB 435 LVL B (0.1%)", "48 hr", 346.00),
            ("PLM CARB 435 LVL B (0.1%)", "72 hr", 261.00),
            ("PLM CARB 435 LVL B (0.1%)", "96 hr", 238.00),
            ("PLM CARB 435 LVL B (0.1%)", "1 Wk", 237.00),

            # PLM Qualitative
            ("PLM Qualitative", "3 hr", 130.00),
            ("PLM Qualitative", "6 hr", 87.00),
            ("PLM Qualitative", "24 hr", 55.00),
            ("PLM Qualitative", "48 hr", 42.50),
            ("PLM Qualitative", "72 hr", 38.00),
            ("PLM Qualitative", "96 hr", 35.25),
            ("PLM Qualitative", "1 Wk", 33.50),

            # New Lead Laboratory Services tests pricing
            # Paint Chips (SW-846-7000B)
            ("Paint Chips (SW-846-7000B)", "3 hr", 43.25),
            ("Paint Chips (SW-846-7000B)", "6 hr", 24.85),
            ("Paint Chips (SW-846-7000B)", "24 hr", 14.45),
            ("Paint Chips (SW-846-7000B)", "48 hr", 12.60),
            ("Paint Chips (SW-846-7000B)", "72 hr", 12.00),
            ("Paint Chips (SW-846-7000B)", "96 hr", 11.35),
            ("Paint Chips (SW-846-7000B)", "1 Wk", 10.05),

            # Air (NIOSH 7082)
            ("Air (NIOSH 7082)", "3 hr", 43.25),
            ("Air (NIOSH 7082)", "6 hr", 24.85),
            ("Air (NIOSH 7082)", "24 hr", 14.45),
            ("Air (NIOSH 7082)", "48 hr", 12.60),
            ("Air (NIOSH 7082)", "72 hr", 12.00),
            ("Air (NIOSH 7082)", "96 hr", 11.35),
            ("Air (NIOSH 7082)", "1 Wk", 10.05),

            # Wipes (SW-846-7000B)
            ("Wipes (SW-846-7000B)", "3 hr", 43.25),
            ("Wipes (SW-846-7000B)", "6 hr", 24.85),
            ("Wipes (SW-846-7000B)", "24 hr", 14.45),
            ("Wipes (SW-846-7000B)", "48 hr", 12.60),
            ("Wipes (SW-846-7000B)", "72 hr", 12.00),
            ("Wipes (SW-846-7000B)", "96 hr", 11.35),
            ("Wipes (SW-846-7000B)", "1 Wk", 10.05),

            # Soil (SW-846-7000B) - "Call" for 3hr
            ("Soil (SW-846-7000B)", "6 hr", 38.00),
            ("Soil (SW-846-7000B)", "24 hr", 21.25),
            ("Soil (SW-846-7000B)", "48 hr", 17.95),
            ("Soil (SW-846-7000B)", "72 hr", 16.45),
            ("Soil (SW-846-7000B)", "96 hr", 15.00),
            ("Soil (SW-846-7000B)", "1 Wk", 14.25),

            # Wastewater (SW-846-7000B) - "Call" for 3hr
            ("Wastewater (SW-846-7000B)", "6 hr", 38.00),
            ("Wastewater (SW-846-7000B)", "24 hr", 21.25),
            ("Wastewater (SW-846-7000B)", "48 hr", 17.95),
            ("Wastewater (SW-846-7000B)", "72 hr", 16.45),
            ("Wastewater (SW-846-7000B)", "96 hr", 15.00),
            ("Wastewater (SW-846-7000B)", "1 Wk", 14.25),

            # Toxicity Characteristic Leaching Procedure (TCLP)
            ("Toxicity Characteristic Leaching Procedure", "30 hr", 273.00),
            ("Toxicity Characteristic Leaching Procedure", "48 hr", 117.00),
            ("Toxicity Characteristic Leaching Procedure", "72 hr", 112.00),
            ("Toxicity Characteristic Leaching Procedure", "96 hr", 105.00),
            ("Toxicity Characteristic Leaching Procedure", "1 Wk", 97.00),

            # New Mold Related Services tests pricing
            # Spore Trap Analysis
            ("Spore Trap Analysis", "Standard", 40.31),
            ("Spore Trap Analysis", "Next Day", 51.61),
            ("Spore Trap Analysis", "Same day", 73.12),
            ("Spore Trap Analysis", "Holiday Wkd", 109.68),

            # Spore Trap Analysis (Clad & Pen/Asp. Differentiation)
            ("Spore Trap Analysis (Clad & Pen/Asp. Differentiation)", "Standard", 74.99),
            ("Spore Trap Analysis (Clad & Pen/Asp. Differentiation)", "Next Day", 112.48),
            ("Spore Trap Analysis (Clad & Pen/Asp. Differentiation)", "Same day", 149.98),
            ("Spore Trap Analysis (Clad & Pen/Asp. Differentiation)", "Holiday Wkd", 224.97),

            # Spore Trap analysis other particles - Supplement
            ("Spore Trap analysis other particles - Supplement", "Standard", 15.05),
            ("Spore Trap analysis other particles - Supplement", "Next Day", 22.57),
            ("Spore Trap analysis other particles - Supplement", "Same day", 30.10),
            ("Spore Trap analysis other particles - Supplement", "Holiday Wkd", 45.15),

            # Culturable air fungi speciation (only Standard pricing)
            ("Culturable air fungi speciation", "Standard", 127.02),

            # Direct Microscopic Examination
            ("Direct Microscopic Examination", "Standard", 32.26),
            ("Direct Microscopic Examination", "Next Day", 45.16),
            ("Direct Microscopic Examination", "Same day", 64.52),
            ("Direct Microscopic Examination", "Holiday Wkd", 96.78),

            # Quantitative spore count direct exam
            ("Quantitative spore count direct exam", "Standard", 36.56),
            ("Quantitative spore count direct exam", "Next Day", 51.61),
            ("Quantitative spore count direct exam", "Same day", 73.12),
            ("Quantitative spore count direct exam", "Holiday Wkd", 96.78),

            # New Environmental Chemistry Laboratory Services tests pricing
            # PCB Bulk Sample Caulking/Concrete/Paint Chips SW 846-3540C8082A (Call for 6hr)
            ("PCB Bulk Sample Caulking/Concrete/Paint Chips SW 846-3540C8082A", "1 Day", 437.00),
            ("PCB Bulk Sample Caulking/Concrete/Paint Chips SW 846-3540C8082A", "2 Day", 325.00),
            ("PCB Bulk Sample Caulking/Concrete/Paint Chips SW 846-3540C8082A", "3 Day", 284.00),
            ("PCB Bulk Sample Caulking/Concrete/Paint Chips SW 846-3540C8082A", "4 Day", 240.00),
            ("PCB Bulk Sample Caulking/Concrete/Paint Chips SW 846-3540C8082A", "1 Wk", 201.00),
            ("PCB Bulk Sample Caulking/Concrete/Paint Chips SW 846-3540C8082A", "2 Wk", 140.00),
        ]

        for test_name, tt_label, price in rates_data:
            test = tests[test_name]
            turn_time = turn_times[tt_label]
            rate = db.query(Rate).filter_by(test_id=test.id, turn_time_id=turn_time.id, lab_id=lab1.id).first()
            if not rate:
                db.add(Rate(test_id=test.id, turn_time_id=turn_time.id, lab_id=lab1.id, price=price))

        db.commit()
        print("✅ Lab1 data seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error while seeding data: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed_lab_fees()