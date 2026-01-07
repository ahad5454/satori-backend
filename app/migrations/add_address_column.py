"""
Migration script to add address column to projects table.

This script adds the address column to the existing projects table.
The column is nullable to support existing projects that don't have an address.
"""
from sqlalchemy import text
from app.database import engine


def migrate():
    """Add address column to projects table."""
    print("Starting migration: Adding address column to projects table...")
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # Add address column if it doesn't exist
            print("Adding address column to projects table...")
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'projects' 
                        AND column_name = 'address'
                    ) THEN
                        ALTER TABLE projects 
                        ADD COLUMN address VARCHAR;
                    END IF;
                END $$;
            """))
            
            # Commit transaction
            trans.commit()
            print("✅ Address column migration completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    migrate()
