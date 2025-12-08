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

app = FastAPI(title=settings.app_name)

# CORS configuration
origins = [
    "https://satori-frontend.vercel.app",  # deployed frontend
    "http://localhost:3000",               # local dev
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

@app.on_event("startup")
def create_tables():
    print("Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)

    # Ensure new column sample_count exists in rates table
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE rates ADD COLUMN IF NOT EXISTS sample_count DOUBLE PRECISION;"))
        conn.commit()
    print("Verified: 'sample_count' column exists in rates table.")

    # Ensure HRS Estimator columns & seed data
    from app.seed.seed_hrs_estimator import ensure_hrs_estimator_columns, seed_hrs_estimator
    try:
        ensure_hrs_estimator_columns()
        print("HRS Estimator columns verified.")
        seed_hrs_estimator()
        print("HRS Estimator reference data seeded.")
    except Exception as e:
        print(f"Warning: Could not setup HRS Estimator: {e}")

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
