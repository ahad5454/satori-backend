import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Satori ERP")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv("DATABASE_URL")
    # SECRET_KEY is mandatory - no default value. App will fail if missing.
    secret_key: str = Field(..., min_length=32)
    # Admin credentials from .env (no hardcoded defaults for security)
    admin_email: str = os.getenv("ADMIN_EMAIL", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")

# Pass secret_key explicitly to trigger validation
settings = Settings(
    secret_key=os.getenv("SECRET_KEY")
)