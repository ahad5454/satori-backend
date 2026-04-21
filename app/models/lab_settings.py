"""
LabSettings model — stores configurable Lab Fee defaults (e.g. markup percentage).
Uses the same simple key/value pattern as LogisticsSettings.
"""
from sqlalchemy import Column, Integer, String
from app.database import Base


class LabSettings(Base):
    __tablename__ = "lab_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
