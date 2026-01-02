from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Index, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class EstimateSnapshot(Base):
    """
    Stores complete estimate snapshots per project.
    
    Each snapshot contains full inputs and outputs for all modules (HRS, Lab, Logistics).
    This allows:
    - Rehydrating module forms when users return
    - Viewing historical estimates
    - Maintaining project-centric estimate history
    
    The 'is_active' flag marks the latest snapshot for a project.
    When a new estimate is generated, the previous active snapshot is marked inactive.
    
    References Project table via project_id foreign key.
    """
    __tablename__ = "estimate_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    project_name = Column(String, nullable=True, index=True)  # Denormalized for backward compatibility during migration
    snapshot_name = Column(String, nullable=True)  # Optional user-friendly name
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Full module data (inputs + outputs) stored as JSON
    # Each module stores both the create payload and the resulting estimation
    hrs_estimator_data = Column(JSON, nullable=True)  # {inputs: {...}, outputs: {...}}
    lab_fees_data = Column(JSON, nullable=True)     # {inputs: {...}, outputs: {...}}
    logistics_data = Column(JSON, nullable=True)    # {inputs: {...}, outputs: {...}}
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship to Project
    project = relationship("Project", backref="snapshots")
    
    # Index for efficient queries
    __table_args__ = (
        Index('idx_project_active', 'project_id', 'is_active'),
    )

