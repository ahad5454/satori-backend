from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import engine, Base
from app.routers import auth, lab_fees  # import new router
from app.models import Admin, Laboratory, ServiceCategory, Test, TurnTime, Rate  # import all models

app = FastAPI(title=settings.app_name)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(lab_fees.router, prefix="/lab-fees", tags=["Lab Fees"])  

# Create tables automatically on startup
@app.on_event("startup")
def create_tables():
    print("Creating database tables if not exist...")
    print("Available tables in metadata:", list(Base.metadata.tables.keys()))
    Base.metadata.create_all(bind=engine)
    print("Database tables ready.")

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
