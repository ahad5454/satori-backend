from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index
from datetime import datetime
from app.database import Base


class Project(Base):
    """
    Central project table - single source of truth for all project information.
    
    This table stores:
    - Unique project identifier (id)
    - Display name (can be non-unique)
    - Summary/aggregated data from all modules
    - Metadata (created, updated, status)
    
    All other tables (EstimateSnapshot, ProjectEstimateSummary, etc.) reference
    this table via project_id foreign key.
    """
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)  # Display name (non-unique)
    description = Column(String, nullable=True)  # Optional project description
    
    # Summary/aggregated data from all modules (for quick access)
    # These are denormalized for performance - updated when modules generate estimates
    hrs_estimator_total = Column(Float, nullable=True, default=None)
    lab_fees_total = Column(Float, nullable=True, default=None)
    logistics_total = Column(Float, nullable=True, default=None)
    grand_total = Column(Float, nullable=True, default=None)
    
    # Latest estimate metadata
    latest_estimate_date = Column(DateTime, nullable=True)  # When last estimate was generated
    latest_snapshot_id = Column(Integer, nullable=True)  # Reference to latest EstimateSnapshot
    
    # Project status/metadata
    status = Column(String, nullable=True, default="active")  # active, archived, completed
    tags = Column(JSON, nullable=True)  # Optional tags for categorization
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_project_name', 'name'),
        Index('idx_project_status', 'status'),
        Index('idx_project_updated', 'updated_at'),
    )

