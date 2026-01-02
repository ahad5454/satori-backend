"""
Utility functions for managing estimate snapshots.

This module provides functions to save/update project estimate snapshots
when modules generate estimates. Snapshots store full inputs and outputs
to enable form rehydration and historical viewing.

UPDATED: Now uses project_id (from Project table) instead of project_name
for proper normalization and to support duplicate project names.
"""
from sqlalchemy.orm import Session
from app.models.estimate_snapshot import EstimateSnapshot
from app.utils.project import get_or_create_project
from typing import Optional, Dict, Any


def save_module_to_snapshot(
    db: Session,
    project_name: Optional[str],
    module_name: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any]
) -> Optional[int]:
    """
    Save or update module data in the active snapshot for a project.
    
    This function:
    1. Gets or creates the project (ensuring unique project_id)
    2. Finds or creates the active snapshot for the project
    3. Updates the module's data (inputs + outputs)
    4. Updates project summary fields
    5. Returns the snapshot ID
    
    Args:
        db: Database session
        project_name: Project name (string identifier) - will create/get Project record
        module_name: Module name ("hrs_estimator", "lab", or "logistics")
        inputs: Full input payload that was sent to the module
        outputs: Full output/result from the module (the created estimation)
    
    Returns:
        Snapshot ID if saved, None if project_name is missing
    
    Note:
        If project_name is None or empty, no snapshot is saved.
        This allows modules to work without a project context.
    """
    if not project_name:
        # Skip saving if no project name provided
        return None
    
    # Get or create project (ensures unique project_id)
    project = get_or_create_project(db, project_name)
    project_id = project.id
    
    # Find active snapshot for this project (by project_id)
    active_snapshot = db.query(EstimateSnapshot).filter(
        EstimateSnapshot.project_id == project_id,
        EstimateSnapshot.is_active == True
    ).first()
    
    if active_snapshot:
        # Update existing active snapshot with module data
        module_data = {
            "inputs": inputs,
            "outputs": outputs
        }
        
        if module_name == "hrs_estimator":
            active_snapshot.hrs_estimator_data = module_data
        elif module_name == "lab":
            active_snapshot.lab_fees_data = module_data
        elif module_name == "logistics":
            active_snapshot.logistics_data = module_data
        
        # Denormalize project_name for backward compatibility
        active_snapshot.project_name = project_name
        
        # updated_at is automatically set by onupdate
        db.flush()
        snapshot_id = active_snapshot.id
    else:
        # Create new active snapshot
        # First, mark any existing active snapshots as inactive (shouldn't happen, but safety)
        db.query(EstimateSnapshot).filter(
            EstimateSnapshot.project_id == project_id,
            EstimateSnapshot.is_active == True
        ).update({"is_active": False})
        
        # Create new snapshot
        snapshot_data = {
            "hrs_estimator_data": None,
            "lab_fees_data": None,
            "logistics_data": None
        }
        
        module_data = {
            "inputs": inputs,
            "outputs": outputs
        }
        
        if module_name == "hrs_estimator":
            snapshot_data["hrs_estimator_data"] = module_data
        elif module_name == "lab":
            snapshot_data["lab_fees_data"] = module_data
        elif module_name == "logistics":
            snapshot_data["logistics_data"] = module_data
        
        new_snapshot = EstimateSnapshot(
            project_id=project_id,
            project_name=project_name,  # Denormalized for backward compatibility
            is_active=True,
            **snapshot_data
        )
        db.add(new_snapshot)
        db.flush()
        snapshot_id = new_snapshot.id
    
    # Update project summary fields (denormalized for quick access)
    from app.utils.project import update_project_summary
    
    # Extract totals from outputs
    hrs_total = None
    lab_total = None
    logistics_total = None
    
    if module_name == "hrs_estimator" and outputs:
        hrs_total = outputs.get("total_cost")
    elif module_name == "lab" and outputs:
        lab_total = outputs.get("total_cost")
    elif module_name == "logistics" and outputs:
        logistics_total = outputs.get("total_logistics_cost")
    
    update_project_summary(
        db=db,
        project_id=project_id,
        hrs_estimator_total=hrs_total,
        lab_fees_total=lab_total,
        logistics_total=logistics_total,
        latest_snapshot_id=snapshot_id
    )
    
    return snapshot_id


def create_new_snapshot_from_active(
    db: Session,
    project_name: str,
    snapshot_name: Optional[str] = None
) -> int:
    """
    Create a new snapshot by duplicating the active snapshot.
    
    This is used when users want to create a new estimate based on
    a previous one. The previous snapshot remains in history.
    
    Args:
        db: Database session
        project_name: Project name (will get/create Project record)
        snapshot_name: Optional name for the new snapshot
    
    Returns:
        ID of the newly created snapshot
    """
    # Get or create project (ensures unique project_id)
    project = get_or_create_project(db, project_name)
    project_id = project.id
    
    # Get active snapshot by project_id
    active = db.query(EstimateSnapshot).filter(
        EstimateSnapshot.project_id == project_id,
        EstimateSnapshot.is_active == True
    ).first()
    
    if not active:
        # No active snapshot, create empty one
        new_snapshot = EstimateSnapshot(
            project_id=project_id,
            project_name=project_name,  # Denormalized for backward compatibility
            snapshot_name=snapshot_name,
            is_active=True
        )
        db.add(new_snapshot)
        db.flush()
        return new_snapshot.id
    
    # Mark old active as inactive
    active.is_active = False
    
    # Create new snapshot with copied data
    new_snapshot = EstimateSnapshot(
        project_id=project_id,
        project_name=project_name,  # Denormalized for backward compatibility
        snapshot_name=snapshot_name,
        is_active=True,
        hrs_estimator_data=active.hrs_estimator_data,
        lab_fees_data=active.lab_fees_data,
        logistics_data=active.logistics_data
    )
    db.add(new_snapshot)
    db.flush()
    return new_snapshot.id

