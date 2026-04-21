"""
Lab Settings Router
Manages admin-configurable defaults for the Lab Fee Calculator module.
Currently supports:
  - lab_markup_default: default markup percentage (e.g. "50")
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.lab_settings import LabSettings
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

LAB_SETTINGS_DEFAULTS = {
    "lab_markup_default": "50",
}


class LabSettingsUpdate(BaseModel):
    lab_markup_default: Optional[str] = None


@router.get("/settings")
def get_lab_settings(db: Session = Depends(get_db)):
    """Return all lab settings as a flat dict, filling in defaults where not set."""
    settings = {}
    rows = db.query(LabSettings).all()
    row_map = {r.key: r.value for r in rows}

    for key, default in LAB_SETTINGS_DEFAULTS.items():
        settings[key] = row_map.get(key, default)

    return settings


@router.put("/settings")
def update_lab_settings(updates: LabSettingsUpdate, db: Session = Depends(get_db)):
    """Upsert one or more lab settings values."""
    update_data = updates.dict(exclude_none=True)

    for key, value in update_data.items():
        if key not in LAB_SETTINGS_DEFAULTS:
            continue
        existing = db.query(LabSettings).filter(LabSettings.key == key).first()
        if existing:
            existing.value = str(value)
        else:
            db.add(LabSettings(key=key, value=str(value)))

    db.commit()
    return get_lab_settings(db)
