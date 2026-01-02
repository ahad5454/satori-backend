"""
Migration script to add project_id columns and create projects table.

This script:
1. Creates the projects table
2. Adds project_id column to estimate_snapshots
3. Adds project_id column to project_estimate_summaries

Run this once to migrate the database schema.
"""
from sqlalchemy import text
from app.database import engine


def migrate():
    """Add project_id columns and create projects table."""
    print("Starting migration: Adding project_id columns...")
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # 1. Create projects table if it doesn't exist
            print("Creating projects table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    description VARCHAR,
                    hrs_estimator_total DOUBLE PRECISION,
                    lab_fees_total DOUBLE PRECISION,
                    logistics_total DOUBLE PRECISION,
                    grand_total DOUBLE PRECISION,
                    latest_estimate_date TIMESTAMP,
                    latest_snapshot_id INTEGER,
                    status VARCHAR DEFAULT 'active',
                    tags JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_project_name ON projects(name)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_project_status ON projects(status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_project_updated ON projects(updated_at)"))
            
            # 2. Add project_id to estimate_snapshots if it doesn't exist
            print("Adding project_id to estimate_snapshots...")
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'estimate_snapshots' 
                        AND column_name = 'project_id'
                    ) THEN
                        ALTER TABLE estimate_snapshots 
                        ADD COLUMN project_id INTEGER;
                    END IF;
                END $$;
            """))
            
            # Add foreign key constraint if it doesn't exist
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'estimate_snapshots_project_id_fkey'
                    ) THEN
                        ALTER TABLE estimate_snapshots 
                        ADD CONSTRAINT estimate_snapshots_project_id_fkey 
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
                    END IF;
                END $$;
            """))
            
            # Create index on project_id if it doesn't exist
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_estimate_snapshots_project_id ON estimate_snapshots(project_id)"))
            
            # 3. Add project_id to project_estimate_summaries if it doesn't exist
            print("Adding project_id to project_estimate_summaries...")
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'project_estimate_summaries' 
                        AND column_name = 'project_id'
                    ) THEN
                        ALTER TABLE project_estimate_summaries 
                        ADD COLUMN project_id INTEGER;
                    END IF;
                END $$;
            """))
            
            # Add foreign key constraint if it doesn't exist
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'project_estimate_summaries_project_id_fkey'
                    ) THEN
                        ALTER TABLE project_estimate_summaries 
                        ADD CONSTRAINT project_estimate_summaries_project_id_fkey 
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
                    END IF;
                END $$;
            """))
            
            # Create index on project_id if it doesn't exist
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_project_estimate_summaries_project_id ON project_estimate_summaries(project_id)"))
            
            # Update unique constraint to use project_id instead of project_name
            # First, drop old constraint if it exists
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'uq_project_module'
                    ) THEN
                        ALTER TABLE project_estimate_summaries 
                        DROP CONSTRAINT IF EXISTS uq_project_module;
                    END IF;
                END $$;
            """))
            
            # Add new unique constraint on (project_id, module_name)
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'uq_project_module_id'
                    ) THEN
                        ALTER TABLE project_estimate_summaries 
                        ADD CONSTRAINT uq_project_module_id 
                        UNIQUE (project_id, module_name);
                    END IF;
                END $$;
            """))
            
            # Update index on estimate_snapshots to use project_id
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = 'idx_project_active'
                    ) THEN
                        DROP INDEX IF EXISTS idx_project_active;
                    END IF;
                END $$;
            """))
            
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_project_active ON estimate_snapshots(project_id, is_active)"))
            
            # Commit transaction
            trans.commit()
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    migrate()

