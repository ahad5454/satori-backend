"""
Project management router.

Provides CRUD operations for projects, which serve as the single source
of truth for all project-related data.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.project import Project
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse
)
from app.utils.project import get_or_create_project, get_project_by_id, update_project_summary

router = APIRouter(tags=["Projects"])


@router.post("/projects/", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new project.
    
    Projects serve as the single source of truth for all project data.
    Each project gets a unique ID, but display names can be duplicated.
    """
    new_project = Project(
        name=project.name,
        address=project.address,
        description=project.description,
        status=project.status or "active",
        tags=project.tags
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@router.get("/projects/", response_model=List[ProjectListResponse])
def list_projects(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all projects with summary data.
    
    Returns projects ordered by most recently updated first.
    Can filter by status (active, archived, completed).
    """
    query = db.query(Project)
    
    if status:
        query = query.filter(Project.status == status)
    
    projects = query.order_by(Project.updated_at.desc()).all()
    return projects


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a project by its unique ID.
    
    This is the recommended way to access a specific project,
    especially when duplicate names exist.
    """
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/by-name/{project_name}", response_model=ProjectResponse)
def get_project_by_name(
    project_name: str,
    db: Session = Depends(get_db)
):
    """
    Get a project by name.
    
    If multiple projects have the same name, returns the most recently updated one.
    For exact matching, use project_id instead.
    """
    from app.utils.project import get_project_by_name as get_by_name
    project = get_by_name(db, project_name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a project's metadata.
    
    Note: This updates display information only. Estimate totals are
    updated automatically when modules generate estimates.
    """
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project_update.name is not None:
        project.name = project_update.name
    if project_update.address is not None:
        project.address = project_update.address
    if project_update.description is not None:
        project.description = project_update.description
    if project_update.status is not None:
        project.status = project_update.status
    if project_update.tags is not None:
        project.tags = project_update.tags
    
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a project and all associated data.
    
    This will cascade delete:
    - All estimate snapshots
    - All project summaries
    - All module estimates (via cascade)
    
    Use with caution - this action cannot be undone.
    """
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

