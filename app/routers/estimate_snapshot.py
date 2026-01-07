from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app import models
from app.models.project_summary import ProjectEstimateSummary
from app.schemas.estimate_snapshot import (
    EstimateSnapshot,
    EstimateSnapshotList,
    EstimateSnapshotCreate,
    ProjectWithSnapshots
)
from app.utils.estimate_snapshot import create_new_snapshot_from_active

router = APIRouter(tags=["Estimate Snapshots"])


@router.get("/projects/{project_name}/snapshot/latest", response_model=EstimateSnapshot)
def get_latest_snapshot(project_name: str, db: Session = Depends(get_db)):
    """
    Get the latest (active) snapshot for a project.
    
    This is used by modules to rehydrate their forms when loaded.
    Returns 404 if no snapshot exists for the project.
    
    NOTE: This endpoint accepts project_name for backward compatibility.
    Internally, it uses project_id from the Project table for proper normalization.
    If multiple projects have the same name, returns the most recently updated one.
    """
    from app.utils.project import get_project_by_name
    
    # Get project by name (most recent if duplicates exist)
    project = get_project_by_name(db, project_name)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_name}' not found"
        )
    
    # Find active snapshot by project_id (proper normalization)
    snapshot = db.query(models.EstimateSnapshot).filter(
        models.EstimateSnapshot.project_id == project.id,
        models.EstimateSnapshot.is_active == True
    ).first()
    
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"No active snapshot found for project: {project_name}"
        )
    
    return snapshot


@router.get("/snapshots/global", response_model=List[ProjectWithSnapshots])
def list_all_snapshots_global(db: Session = Depends(get_db)):
    """
    Get global estimate history: all projects with their snapshots.
    
    This endpoint returns ALL projects (not just ones with snapshots),
    grouped by project. Uses Project table as single source of truth.
    Projects without snapshots will have an empty snapshots list.
    This provides a global view of all projects and their estimates.
    
    Does NOT require a project_name parameter.
    """
    # Get ALL projects from the Project table (not just ones with snapshots)
    # This ensures consistency with /select-project which shows all projects
    all_projects = db.query(models.Project).filter(
        models.Project.status == "active"  # Only show active projects, matching /select-project behavior
    ).all()
    
    if not all_projects:
        # No projects in database, return empty list
        return []
    
    # Process all projects (including those without snapshots)
    result = []
    for project in all_projects:
        # Get all snapshots for this project (by project_id)
        snapshots = db.query(models.EstimateSnapshot).filter(
            models.EstimateSnapshot.project_id == project.id
        ).order_by(models.EstimateSnapshot.created_at.desc()).all()
        
        # Convert to EstimateSnapshotList format
        snapshot_list = []
        for snapshot in snapshots:
            # Extract totals from module data
            hrs_total = None
            lab_total = None
            logistics_total = None
            
            if snapshot.hrs_estimator_data and snapshot.hrs_estimator_data.get("outputs"):
                hrs_total = snapshot.hrs_estimator_data["outputs"].get("total_cost")
            
            if snapshot.lab_fees_data and snapshot.lab_fees_data.get("outputs"):
                lab_total = snapshot.lab_fees_data["outputs"].get("total_cost")
            
            if snapshot.logistics_data and snapshot.logistics_data.get("outputs"):
                logistics_total = snapshot.logistics_data["outputs"].get("total_logistics_cost")
            
            grand_total = sum(
                (t if t is not None else 0.0) 
                for t in [hrs_total, lab_total, logistics_total]
            )
            
            snapshot_list.append(EstimateSnapshotList(
                id=snapshot.id,
                project_name=snapshot.project_name,
                snapshot_name=snapshot.snapshot_name,
                is_active=snapshot.is_active,
                created_at=snapshot.created_at,
                updated_at=snapshot.updated_at,
                hrs_estimator_total=hrs_total,
                lab_fees_total=lab_total,
                logistics_total=logistics_total,
                grand_total=round(grand_total, 2) if grand_total else None
            ))
        
        result.append(ProjectWithSnapshots(
            project_id=project.id,  # Include project ID for deletion
            project_name=project.name,  # Use project.name from Project table
            created_at=project.created_at,  # Include project creation date
            snapshots=snapshot_list
        ))
    
    # Sort by creation date (most recent first), then by name if dates are equal
    result.sort(key=lambda x: (x.created_at or datetime.min, x.project_name), reverse=True)
    
    return result


@router.get("/projects/{project_name}/snapshots", response_model=List[EstimateSnapshotList])
def list_project_snapshots(project_name: str, db: Session = Depends(get_db)):
    """
    List all snapshots for a project, ordered by creation date (newest first).
    
    Returns summary information including module totals for quick reference.
    
    NOTE: This endpoint accepts project_name for backward compatibility.
    Internally, it uses project_id from the Project table for proper normalization.
    """
    from app.utils.project import get_project_by_name
    
    # Get project by name (most recent if duplicates exist)
    project = get_project_by_name(db, project_name)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_name}' not found"
        )
    
    # Get all snapshots for this project (by project_id)
    snapshots = db.query(models.EstimateSnapshot).filter(
        models.EstimateSnapshot.project_id == project.id
    ).order_by(models.EstimateSnapshot.created_at.desc()).all()
    
    result = []
    for snapshot in snapshots:
        # Extract totals from module data
        hrs_total = None
        lab_total = None
        logistics_total = None
        
        if snapshot.hrs_estimator_data and snapshot.hrs_estimator_data.get("outputs"):
            hrs_total = snapshot.hrs_estimator_data["outputs"].get("total_cost")
        
        if snapshot.lab_fees_data and snapshot.lab_fees_data.get("outputs"):
            lab_total = snapshot.lab_fees_data["outputs"].get("total_cost")
        
        if snapshot.logistics_data and snapshot.logistics_data.get("outputs"):
            logistics_total = snapshot.logistics_data["outputs"].get("total_logistics_cost")
        
        grand_total = sum(
            (t if t is not None else 0.0) 
            for t in [hrs_total, lab_total, logistics_total]
        )
        
        result.append(EstimateSnapshotList(
            id=snapshot.id,
            project_name=snapshot.project_name,
            snapshot_name=snapshot.snapshot_name,
            is_active=snapshot.is_active,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
            hrs_estimator_total=hrs_total,
            lab_fees_total=lab_total,
            logistics_total=logistics_total,
            grand_total=round(grand_total, 2) if grand_total else None
        ))
    
    return result


@router.get("/snapshots/{snapshot_id}", response_model=EstimateSnapshot)
def get_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    """
    Get a specific snapshot by ID.
    
    Returns full snapshot data including all module inputs and outputs.
    """
    snapshot = db.query(models.EstimateSnapshot).filter(
        models.EstimateSnapshot.id == snapshot_id
    ).first()
    
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"Snapshot with ID {snapshot_id} not found"
        )
    
    return snapshot


@router.post("/projects/{project_name}/snapshots/duplicate", response_model=EstimateSnapshot)
def duplicate_active_snapshot(
    project_name: str,
    snapshot_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create a new snapshot by duplicating the active snapshot.
    
    This allows users to create a new estimate based on a previous one.
    The previous snapshot remains in history, and the new one becomes active.
    
    Args:
        project_name: Project name
        snapshot_name: Optional name for the new snapshot
    """
    new_snapshot_id = create_new_snapshot_from_active(
        db=db,
        project_name=project_name,
        snapshot_name=snapshot_name
    )
    
    db.commit()
    
    # Fetch and return the new snapshot
    new_snapshot = db.query(models.EstimateSnapshot).filter(
        models.EstimateSnapshot.id == new_snapshot_id
    ).first()
    
    if not new_snapshot:
        raise HTTPException(
            status_code=500,
            detail="Failed to create duplicate snapshot"
        )
    
    return new_snapshot


@router.post("/projects/{project_name}/snapshot/save-and-close")
def save_and_close_project(project_name: str, db: Session = Depends(get_db)):
    """
    Save & Close Project: Ensures the active snapshot is up-to-date and marked as latest.
    
    This endpoint:
    - Gets or creates the project (ensures unique project_id)
    - Ensures an active snapshot exists for the project
    - Updates the snapshot with any latest data from generated estimates
    - Does NOT create new estimates or auto-submit form data
    - Only commits data that has already been generated via module endpoints
    
    This represents an explicit commit of the project's current estimate state.
    
    NOTE: This endpoint accepts project_name for backward compatibility.
    Internally, it uses project_id from the Project table.
    """
    from app.utils.project import get_or_create_project
    
    # Get or create project (ensures unique project_id)
    project = get_or_create_project(db, project_name)
    
    # Get or create active snapshot (by project_id)
    active_snapshot = db.query(models.EstimateSnapshot).filter(
        models.EstimateSnapshot.project_id == project.id,
        models.EstimateSnapshot.is_active == True
    ).first()
    
    if not active_snapshot:
        # Create empty active snapshot if none exists
        # This ensures the project has a snapshot even if no estimates were generated
        active_snapshot = models.EstimateSnapshot(
            project_id=project.id,
            project_name=project_name,  # Denormalized for backward compatibility
            is_active=True,
            hrs_estimator_data=None,
            lab_fees_data=None,
            logistics_data=None
        )
        db.add(active_snapshot)
    
    # Ensure snapshot is marked as active (should already be, but safety check)
    active_snapshot.is_active = True
    
    # Update project's latest_snapshot_id
    from app.utils.project import update_project_summary
    update_project_summary(
        db=db,
        project_id=project.id,
        latest_snapshot_id=active_snapshot.id
    )
    
    # Note: We don't fetch latest estimates here because they're already saved
    # to the snapshot when generated. This endpoint is just a commit action.
    
    db.commit()
    
    return {
        "message": "Project saved and closed successfully",
        "snapshot_id": active_snapshot.id
    }


@router.delete("/projects/{project_name}/discard")
def discard_project(project_name: str, db: Session = Depends(get_db)):
    """
    Discard Project Details: Permanently deletes all snapshots and summaries for a project.
    
    This endpoint:
    - Deletes all EstimateSnapshot records for the project
    - Deletes all ProjectEstimateSummary records for the project
    - Deletes the Project record itself
    - Leaves no residual data
    
    This represents a full rollback of the project's current estimate state.
    
    NOTE: This endpoint accepts project_name for backward compatibility.
    Internally, it uses project_id from the Project table.
    """
    from app.utils.project import get_project_by_name
    
    # Get project by name
    project = get_project_by_name(db, project_name)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_name}' not found"
        )
    
    project_id = project.id
    
    # Delete all snapshots for this project (by project_id)
    deleted_snapshots = db.query(models.EstimateSnapshot).filter(
        models.EstimateSnapshot.project_id == project_id
    ).delete()
    
    # Delete all project summaries for this project (by project_id)
    deleted_summaries = db.query(ProjectEstimateSummary).filter(
        ProjectEstimateSummary.project_id == project_id
    ).delete()
    
    # Delete the Project record itself
    db.delete(project)
    
    db.commit()
    
    return {
        "message": "Project discarded successfully",
        "deleted_snapshots": deleted_snapshots,
        "deleted_summaries": deleted_summaries
    }


@router.delete("/snapshots/{snapshot_id}")
def delete_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    """
    Delete a specific estimate snapshot.
    
    If the deleted snapshot was active:
    - Sets the most recent remaining snapshot (by updated_at) as active
    - If no snapshots remain, the project has no active snapshot
    
    This permanently removes the snapshot and cannot be undone.
    """
    # Get the snapshot to delete
    snapshot = db.query(models.EstimateSnapshot).filter(
        models.EstimateSnapshot.id == snapshot_id
    ).first()
    
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"Snapshot with ID {snapshot_id} not found"
        )
    
    project_id = snapshot.project_id
    was_active = snapshot.is_active
    
    # Delete the snapshot
    db.delete(snapshot)
    db.flush()
    
    # If it was active, set the most recent remaining snapshot as active
    new_active_set = False
    if was_active:
        remaining_snapshots = db.query(models.EstimateSnapshot).filter(
            models.EstimateSnapshot.project_id == project_id
        ).order_by(models.EstimateSnapshot.updated_at.desc()).all()
        
        if remaining_snapshots:
            # Set the most recent one as active
            remaining_snapshots[0].is_active = True
            # Ensure others are inactive
            for s in remaining_snapshots[1:]:
                s.is_active = False
            new_active_set = True
        # If no snapshots remain, project has no active snapshot (as intended)
    
    db.commit()
    
    return {
        "message": "Snapshot deleted successfully",
        "was_active": was_active,
        "new_active_set": new_active_set
    }

