"""
Utility functions for managing project estimate summaries.

This module provides functions to save/update module-level estimate totals
when estimates are generated. The summary table is read-only from the
summary page perspective.

UPDATED: Now uses project_id (from Project table) instead of project_name
for proper normalization and to support duplicate project names.
"""
from sqlalchemy.orm import Session
from app.models.project_summary import ProjectEstimateSummary
from app.utils.project import get_or_create_project
from typing import Optional, Dict, Any


def save_or_update_module_summary(
    db: Session,
    project_name: Optional[str],
    module_name: str,
    estimate_total: float,
    estimate_breakdown: Optional[Dict[str, Any]] = None
) -> None:
    """
    Save or update the latest estimate summary for a module and project.
    
    If a summary already exists for this project+module, it is updated.
    Otherwise, a new summary is created.
    
    Also updates the Project table's denormalized summary fields for quick access.
    
    Args:
        db: Database session
        project_name: Project name (string identifier) - will get/create Project record
        module_name: Module name ("hrs_estimator", "lab", or "logistics")
        estimate_total: Total estimate amount for this module
        estimate_breakdown: Optional detailed breakdown (JSON)
    
    Note:
        If project_name is None or empty, no summary is saved.
        This allows modules to work without a project context.
    """
    if not project_name:
        # Skip saving if no project name provided
        return
    
    # Get or create project (ensures unique project_id)
    project = get_or_create_project(db, project_name)
    project_id = project.id
    
    # Find existing summary or create new one (by project_id)
    summary = db.query(ProjectEstimateSummary).filter(
        ProjectEstimateSummary.project_id == project_id,
        ProjectEstimateSummary.module_name == module_name
    ).first()
    
    if summary:
        # Update existing summary
        summary.estimate_total = estimate_total
        summary.estimate_breakdown = estimate_breakdown
        # Denormalize project_name for backward compatibility
        summary.project_name = project_name
        # updated_at is automatically set by onupdate
    else:
        # Create new summary
        summary = ProjectEstimateSummary(
            project_id=project_id,
            project_name=project_name,  # Denormalized for backward compatibility
            module_name=module_name,
            estimate_total=estimate_total,
            estimate_breakdown=estimate_breakdown
        )
        db.add(summary)
    
    # Update Project table's denormalized summary fields (for quick access)
    from app.utils.project import update_project_summary
    
    hrs_total = None
    lab_total = None
    logistics_total = None
    
    if module_name == "hrs_estimator":
        hrs_total = estimate_total
    elif module_name == "lab":
        lab_total = estimate_total
    elif module_name == "logistics":
        logistics_total = estimate_total
    
    update_project_summary(
        db=db,
        project_id=project_id,
        hrs_estimator_total=hrs_total,
        lab_fees_total=lab_total,
        logistics_total=logistics_total
    )
    
    # Note: Caller is responsible for committing the transaction

