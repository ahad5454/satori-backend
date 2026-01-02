from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProjectBase(BaseModel):
    """Base schema for Project"""
    name: str
    description: Optional[str] = None
    status: Optional[str] = "active"
    tags: Optional[List[str]] = None


class ProjectCreate(ProjectBase):
    """Schema for creating a new project"""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


class ProjectResponse(ProjectBase):
    """Schema for project response"""
    id: int
    hrs_estimator_total: Optional[float] = None
    lab_fees_total: Optional[float] = None
    logistics_total: Optional[float] = None
    grand_total: Optional[float] = None
    latest_estimate_date: Optional[datetime] = None
    latest_snapshot_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for listing projects with summary"""
    id: int
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    hrs_estimator_total: Optional[float] = None
    lab_fees_total: Optional[float] = None
    logistics_total: Optional[float] = None
    grand_total: Optional[float] = None
    latest_estimate_date: Optional[datetime] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True

