from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ProjectEstimateSummary(Base):
    """
    Stores the latest estimate total per module per project.
    
    This table is read-only from the summary page perspective.
    Estimates are automatically saved/updated when modules generate estimates.
    
    One row per project per module (latest estimate only).
    
    NOTE: This table may be deprecated in favor of denormalized fields in Project table,
    but kept for backward compatibility and as a detailed breakdown source.
    """
    __tablename__ = "project_estimate_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    project_name = Column(String, nullable=True, index=True)  # Denormalized for backward compatibility during migration
    module_name = Column(String, nullable=False)  # "hrs_estimator", "lab", "logistics"
    estimate_total = Column(Float, nullable=False, default=0.0)
    estimate_breakdown = Column(JSON, nullable=True)  # Optional detailed breakdown
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to Project
    project = relationship("Project", backref="summaries")
    
    # Ensure one summary per project per module
    __table_args__ = (
        UniqueConstraint('project_id', 'module_name', name='uq_project_module'),
    )

