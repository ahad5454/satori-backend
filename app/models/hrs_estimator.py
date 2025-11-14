from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

# ---- Top-level estimation "session" ----
class HRSEstimation(Base):
    __tablename__ = "hrs_estimations"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, nullable=True)

    # minutes per sample - defaults captured (snapshot at time of estimate)
    default_minutes_asbestos = Column(Float, nullable=False, default=15.0)
    default_minutes_xrf = Column(Float, nullable=False, default=3.0)
    default_minutes_lead = Column(Float, nullable=False, default=10.0)
    default_minutes_mold = Column(Float, nullable=False, default=20.0)

    # user overrides (audit)
    override_minutes_asbestos = Column(Float, nullable=True)
    override_minutes_xrf = Column(Float, nullable=True)
    override_minutes_lead = Column(Float, nullable=True)
    override_minutes_mold = Column(Float, nullable=True)

    # field staff adjustment
    field_staff_count = Column(Integer, nullable=False, default=1)
    efficiency_factor = Column(Float, nullable=False, default=1.0)

    # rolled-up counts
    total_plm = Column(Float, nullable=False, default=0.0)
    total_xrf_shots = Column(Float, nullable=False, default=0.0)
    total_chips_wipes = Column(Float, nullable=False, default=0.0)
    total_tape_lift = Column(Float, nullable=False, default=0.0)
    total_spore_trap = Column(Float, nullable=False, default=0.0)
    total_culturable = Column(Float, nullable=False, default=0.0)
    orm_hours = Column(Float, nullable=False, default=0.0)

    # suggested hours (base & final)
    suggested_hours_base = Column(Float, nullable=False, default=0.0)
    suggested_hours_final = Column(Float, nullable=False, default=0.0)

    # NEW: role + cost fields
    selected_role = Column(String, nullable=True)            # "Env Scientist" or "Env Technician"
    calculated_cost = Column(Float, nullable=True)           # hours × rate
    manual_labor_hours = Column(JSON, nullable=True)         # {"Program Manager": 5, "Accounting": 2}
    manual_labor_costs = Column(JSON, nullable=True)         # {"Program Manager": 657.75, ...}
    total_cost = Column(Float, nullable=True)                # Total combined cost

    # optional labor breakdown (hours)
    labor_breakdown = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    asbestos_lines = relationship("AsbestosComponentLine", back_populates="estimation", cascade="all, delete-orphan")
    lead_lines = relationship("LeadComponentLine", back_populates="estimation", cascade="all, delete-orphan")
    mold_lines = relationship("MoldComponentLine", back_populates="estimation", cascade="all, delete-orphan")
    orm_record = relationship("OtherRegulatedMaterials", back_populates="estimation", uselist=False, cascade="all, delete-orphan")


# ---- Asbestos: Actuals * Bulks per Unit = Bulk Summary ----
class AsbestosComponentLine(Base):
    __tablename__ = "hrs_asbestos_lines"

    id = Column(Integer, primary_key=True, index=True)
    estimation_id = Column(Integer, ForeignKey("hrs_estimations.id"), nullable=False)
    component_name = Column(String, nullable=False)
    unit_label = Column(String, nullable=False)
    actuals = Column(Float, nullable=False, default=0.0)
    bulks_per_unit = Column(Float, nullable=False, default=0.0)
    bulk_summary = Column(Float, nullable=False, default=0.0)

    estimation = relationship("HRSEstimation", back_populates="asbestos_lines")


# ---- Lead ----
class LeadComponentLine(Base):
    __tablename__ = "hrs_lead_lines"

    id = Column(Integer, primary_key=True, index=True)
    estimation_id = Column(Integer, ForeignKey("hrs_estimations.id"), nullable=False)
    component_name = Column(String, nullable=False)
    xrf_shots = Column(Float, nullable=False, default=0.0)
    chips_wipes = Column(Float, nullable=False, default=0.0)

    estimation = relationship("HRSEstimation", back_populates="lead_lines")


# ---- Mold ----
class MoldComponentLine(Base):
    __tablename__ = "hrs_mold_lines"

    id = Column(Integer, primary_key=True, index=True)
    estimation_id = Column(Integer, ForeignKey("hrs_estimations.id"), nullable=False)
    component_name = Column(String, nullable=False)
    tape_lift = Column(Float, nullable=False, default=0.0)
    spore_trap = Column(Float, nullable=False, default=0.0)
    culturable = Column(Float, nullable=False, default=0.0)

    estimation = relationship("HRSEstimation", back_populates="mold_lines")


# ---- ORM ----
class OtherRegulatedMaterials(Base):
    __tablename__ = "hrs_orm_record"

    id = Column(Integer, primary_key=True, index=True)
    estimation_id = Column(Integer, ForeignKey("hrs_estimations.id"), nullable=False)
    building_total_sf = Column(Float, nullable=True)
    hours = Column(Float, nullable=False, default=0.0)

    estimation = relationship("HRSEstimation", back_populates="orm_record")


# ---- Reference Tables ----
class SamplingDefault(Base):
    __tablename__ = "hrs_sampling_defaults"
    id = Column(Integer, primary_key=True, index=True)
    sampling_type = Column(String, unique=True, nullable=False)
    minutes_per_sample = Column(Float, nullable=False)


class ComponentList(Base):
    __tablename__ = "hrs_component_list"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    component_name = Column(String, nullable=False)


class LaborRate(Base):
    __tablename__ = "hrs_labor_rates"
    id = Column(Integer, primary_key=True, index=True)
    labor_role = Column(String, unique=True, nullable=False)
    hourly_rate = Column(Float, nullable=False)
