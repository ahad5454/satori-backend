from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.database import engine, Base
from app.models import *

# HRS Estimator models (must remain untouched)
from app.models.hrs_estimator import (
    HRSEstimation,
    AsbestosComponentLine,
    LeadComponentLine,
    MoldComponentLine,
    OtherRegulatedMaterials
)

from app.models.logistics import LogisticsEstimation

from app.routers import auth, lab_fees
from app.routers import hrs_estimator

# Logistics router import
from app.routers import logistics

# Project Summary router import
from app.routers import project_summary

# Estimate Snapshot router import
from app.routers import estimate_snapshot

# Project router import
from app.routers import project

app = FastAPI(title=settings.app_name)

# CORS configuration
origins = [
    "https://satori-erp-production-8gmcx.ondigitalocean.app", # REAL production URL
    "http://localhost:3000",   
    "http://127.0.0.1:3000",           
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(lab_fees.router, prefix="/lab-fees", tags=["Lab Fees"])
app.include_router(hrs_estimator.router, prefix="/hrs-estimator", tags=["HRS Estimator"])

# NEW: Logistics router
app.include_router(logistics.router, prefix="/logistics", tags=["Logistics"])

# NEW: Project Summary router
app.include_router(project_summary.router, tags=["Project Summary"])

# NEW: Estimate Snapshot router
app.include_router(estimate_snapshot.router, tags=["Estimate Snapshots"])

# NEW: Project router
app.include_router(project.router, tags=["Projects"])

# NEW: User Management router
from app.routers import users
app.include_router(users.router, tags=["User Management"])

@app.on_event("startup")
def create_tables():
    print("Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)

    # Run migration to add project_id columns
    try:
        from app.migrations.add_project_id_columns import migrate
        migrate()
        print("✅ Project ID migration completed.")
    except Exception as e:
        # Migration errors are non-fatal - columns might already exist
        import traceback
        print(f"⚠️  Migration note: {str(e)}")
        print("   (This is normal if columns already exist or on first run)")

    # Run migration to add address column to projects table
    try:
        from app.migrations.add_address_column import migrate as migrate_address
        migrate_address()
        print("✅ Address column migration completed.")
    except Exception as e:
        # Migration errors are non-fatal - column might already exist
        print(f"⚠️  Address migration note: {str(e)}")
        print("   (This is normal if column already exists)")

    # Ensure new column sample_count exists in rates table
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE rates ADD COLUMN IF NOT EXISTS sample_count DOUBLE PRECISION;"))
        conn.commit()
    print("Verified: 'sample_count' column exists in rates table.")

    # Ensure HRS Estimator columns & seed data
    # STRICT PRODUCTION RULE: No auto-seeding in production
    if settings.environment.lower() != "production":
        from app.seed.seed_hrs_estimator import ensure_hrs_estimator_columns, seed_hrs_estimator
        try:
            ensure_hrs_estimator_columns()
            print("HRS Estimator columns verified.")
            seed_hrs_estimator()
            print("HRS Estimator reference data seeded.")
        except Exception as e:
            print(f"Warning: Could not setup HRS Estimator: {e}")
    else:
        print("🔐 Production environment detected: Skipping auto-seeding.")

    # Seed default admin from .env (always runs - ensures admin exists)
    from app.models.admin import Admin
    from app.core.security import hash_password
    from sqlalchemy.orm import Session
    
    # Only seed if admin credentials are configured
    if settings.admin_email and settings.admin_password:
        db = Session(bind=engine)
        try:
            existing_admin = db.query(Admin).filter(Admin.email == settings.admin_email).first()
            if not existing_admin:
                # Truncate password to 72 bytes for bcrypt compatibility
                password = settings.admin_password[:72]
                # Extract username from email (part before @)
                username = settings.admin_email.split('@')[0]
                admin_user = Admin(
                    username=username,
                    email=settings.admin_email,
                    hashed_password=hash_password(password),
                    role="admin"
                )
                db.add(admin_user)
                db.commit()
                print(f"✅ Default admin created: {settings.admin_email}")
            else:
                # Ensure existing admin has admin role
                if existing_admin.role != "admin":
                    existing_admin.role = "admin"
                    db.commit()
                    print(f"✅ Admin role verified for: {settings.admin_email}")
                else:
                    print(f"✅ Admin exists: {settings.admin_email}")
        except Exception as e:
            print(f"⚠️ Could not seed admin: {e}")
            db.rollback()
        finally:
            db.close()
    else:
        print("⚠️ ADMIN_EMAIL or ADMIN_PASSWORD not set in .env - skipping admin seeding")

    print("Database ready.")


@app.get("/", response_class=HTMLResponse)
def root():
    return f"""
    <html>
        <head>
            <title>{settings.app_name}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f9f9f9;
                    display: flex;
                    height: 100vh;
                    justify-content: center;
                    align-items: center;
                }}
                h1 {{
                    color: #2c3e50;
                    font-size: 3em;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <h1>{settings.app_name} is running!</h1>
        </body>
    </html>
    """
