from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class EstimateSnapshotBase(BaseModel):
    project_name: str
    snapshot_name: Optional[str] = None


class EstimateSnapshotCreate(EstimateSnapshotBase):
    """Schema for creating a new snapshot (typically done automatically)"""
    pass


class EstimateSnapshotUpdate(BaseModel):
    """Schema for updating snapshot data"""
    snapshot_name: Optional[str] = None
    hrs_estimator_data: Optional[Dict[str, Any]] = None
    lab_fees_data: Optional[Dict[str, Any]] = None
    logistics_data: Optional[Dict[str, Any]] = None


class EstimateSnapshot(EstimateSnapshotBase):
    """Schema for reading snapshot data"""
    id: int
    is_active: bool
    hrs_estimator_data: Optional[Dict[str, Any]] = None
    lab_fees_data: Optional[Dict[str, Any]] = None
    logistics_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EstimateSnapshotList(BaseModel):
    """Schema for listing snapshots (summary view)"""
    id: int
    project_name: str
    snapshot_name: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # Module totals for quick reference
    hrs_estimator_total: Optional[float] = None
    lab_fees_total: Optional[float] = None
    logistics_total: Optional[float] = None
    grand_total: Optional[float] = None
    
    class Config:
        from_attributes = True


class ProjectWithSnapshots(BaseModel):
    """Schema for a project with its snapshots (for global history)"""
    project_id: Optional[int] = None  # Project ID for deletion
    project_name: str
    created_at: Optional[datetime] = None  # Project creation date for sorting
    snapshots: List[EstimateSnapshotList]
    
    class Config:
        from_attributes = True

