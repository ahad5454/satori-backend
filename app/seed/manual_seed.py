import os
import sys

# Ensure backend directory is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from app.core.config import settings
from app.seed.seed_hrs_estimator import ensure_hrs_estimator_columns, seed_hrs_estimator

def main():
    print("WARNING: This script will seed the database with initial data.")
    print(f"Target Environment: {settings.environment}")
    print(f"Database: {settings.database_url.split('@')[-1] if settings.database_url else 'Unknown'}")
    
    confirm = input("Are you sure you want to proceed? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted.")
        return

    try:
        print("Ensuring columns exist...")
        ensure_hrs_estimator_columns()
        print("Seeding HRS Estimator data...")
        seed_hrs_estimator()
        print("✅ Seeding completed successfully.")
    except Exception as e:
        print(f"❌ Seeding failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
