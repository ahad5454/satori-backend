"""
Utility functions for managing projects.

This module provides functions to get or create projects, ensuring
that projects are properly tracked with unique IDs while allowing
duplicate display names.
"""
from sqlalchemy.orm import Session
from app.models.project import Project
from typing import Optional
from datetime import datetime


def get_or_create_project(
    db: Session,
    project_name: str,
    description: Optional[str] = None,
    address: Optional[str] = None
) -> Project:
    """
    Get an existing project by name, or create a new one if it doesn't exist.
    
    This function ensures that:
    - Projects are properly tracked with unique IDs
    - Duplicate project names are allowed (each gets its own ID)
    - Projects are created on-demand when first referenced
    
    Args:
        db: Database session
        project_name: Display name for the project (can be non-unique)
        description: Optional project description
    
    Returns:
        Project instance (existing or newly created)
    
    Note:
        If multiple projects have the same name, this will return the most
        recently updated one. For exact matching, use get_project_by_id instead.
    """
    if not project_name:
        raise ValueError("Project name cannot be empty")
    
    # Try to find existing project by name (most recent first)
    # In the future, you might want to add user_id or other filters here
    project = db.query(Project).filter(
        Project.name == project_name
    ).order_by(Project.updated_at.desc()).first()
    
    if project:
        return project
    
    # Create new project
    project = Project(
        name=project_name,
        address=address,
        description=description,
        status="active"
    )
    db.add(project)
    db.flush()  # Get the ID without committing
    return project


def get_project_by_id(db: Session, project_id: int) -> Optional[Project]:
    """
    Get a project by its unique ID.
    
    Args:
        db: Database session
        project_id: Unique project ID
    
    Returns:
        Project instance if found, None otherwise
    """
    return db.query(Project).filter(Project.id == project_id).first()


def get_project_by_name(db: Session, project_name: str) -> Optional[Project]:
    """
    Get a project by name (returns most recent if duplicates exist).
    
    Args:
        db: Database session
        project_name: Project display name
    
    Returns:
        Most recently updated Project instance if found, None otherwise
    
    Note:
        If multiple projects have the same name, this returns the most recent.
        For exact matching, consider using project_id instead.
    """
    if not project_name:
        return None
    
    return db.query(Project).filter(
        Project.name == project_name
    ).order_by(Project.updated_at.desc()).first()


def update_project_summary(
    db: Session,
    project_id: int,
    hrs_estimator_total: Optional[float] = None,
    lab_fees_total: Optional[float] = None,
    logistics_total: Optional[float] = None,
    latest_snapshot_id: Optional[int] = None
) -> None:
    """
    Update the summary/aggregated fields in the Project table.
    
    This denormalizes data for quick access without querying related tables.
    
    Args:
        db: Database session
        project_id: Unique project ID
        hrs_estimator_total: Latest HRS estimator total
        lab_fees_total: Latest Lab Fees total
        logistics_total: Latest Logistics total
        latest_snapshot_id: ID of the latest snapshot
    
    Note:
        Caller is responsible for committing the transaction.
    """
    project = get_project_by_id(db, project_id)
    if not project:
        return
    
    if hrs_estimator_total is not None:
        project.hrs_estimator_total = hrs_estimator_total
    if lab_fees_total is not None:
        project.lab_fees_total = lab_fees_total
    if logistics_total is not None:
        project.logistics_total = logistics_total
    if latest_snapshot_id is not None:
        project.latest_snapshot_id = latest_snapshot_id
    
    # Calculate grand total
    totals = [
        project.hrs_estimator_total or 0.0,
        project.lab_fees_total or 0.0,
        project.logistics_total or 0.0
    ]
    project.grand_total = sum(totals) if any(totals) else None
    project.latest_estimate_date = datetime.utcnow()
    
    db.flush()

