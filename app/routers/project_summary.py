from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Optional
from app.database import get_db
from app import models
from app.schemas.project_summary import ProjectEstimateSummaryResponse

router = APIRouter(tags=["Project Summary"])


@router.get("/projects/{project_name}/estimate-summary", response_model=ProjectEstimateSummaryResponse)
def get_project_estimate_summary(project_name: str, db: Session = Depends(get_db)):
    """
    Get the project estimate summary for a given project.
    
    Returns module-level totals and a grand total.
    Missing modules are represented as null (not errors).
    
    This endpoint is read-only and does not trigger any calculations.
    
    NOTE: This endpoint accepts project_name for backward compatibility.
    Internally, it uses project_id from the Project table for proper normalization.
    Also checks Project table's denormalized summary fields for quick access.
    """
    from app.utils.project import get_project_by_name
    
    # Get project by name (most recent if duplicates exist)
    project = get_project_by_name(db, project_name)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_name}' not found"
        )
    
    # Try to get summary from Project table first (denormalized for performance)
    # If Project table has summary data, use it; otherwise fall back to ProjectEstimateSummary table
    modules: Dict[str, Optional[float]] = {
        "hrs_estimator": project.hrs_estimator_total,
        "lab": project.lab_fees_total,
        "logistics": project.logistics_total
    }
    
    # If Project table doesn't have summary data, fetch from ProjectEstimateSummary table
    if all(v is None for v in modules.values()):
        summaries = db.query(models.ProjectEstimateSummary).filter(
            models.ProjectEstimateSummary.project_id == project.id
        ).all()
        
        # Reset modules dict
        modules = {
            "hrs_estimator": None,
            "lab": None,
            "logistics": None
        }
        
        # Populate with actual values from database
        for summary in summaries:
            if summary.module_name in modules:
                modules[summary.module_name] = summary.estimate_total
    
    # Calculate grand total (treat None as 0)
    grand_total = sum(
        (total if total is not None else 0.0) 
        for total in modules.values()
    )
    
    return ProjectEstimateSummaryResponse(
        project_name=project.name,  # Use project.name from Project table
        modules=modules,
        grand_total=round(grand_total, 2)
    )

