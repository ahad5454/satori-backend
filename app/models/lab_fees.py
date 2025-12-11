from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Laboratory(Base):
    __tablename__ = "laboratories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    address = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)

    # Relationships
    service_categories = relationship("ServiceCategory", back_populates="laboratory")
    rates = relationship("Rate", back_populates="laboratory")


class ServiceCategory(Base):
    __tablename__ = "service_categories"

    id = Column(Integer, primary_key=True, index=True)
    lab_id = Column(Integer, ForeignKey("laboratories.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Relationships
    laboratory = relationship("Laboratory", back_populates="service_categories")
    tests = relationship("Test", back_populates="service_category")


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    service_category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=False)
    name = Column(String, nullable=False)

    # Relationships
    service_category = relationship("ServiceCategory", back_populates="tests")
    rates = relationship("Rate", back_populates="test")


class TurnTime(Base):
    __tablename__ = "turn_times"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, unique=True, nullable=False)
    hours = Column(Integer, nullable=True)

    rates = relationship("Rate", back_populates="turn_time")


class Rate(Base):
    __tablename__ = "rates"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    turn_time_id = Column(Integer, ForeignKey("turn_times.id"), nullable=False)
    lab_id = Column(Integer, ForeignKey("laboratories.id"), nullable=False)
    price = Column(Float, nullable=False)
    sample_count = Column(Float, nullable=True)  

    # Relationships
    test = relationship("Test", back_populates="rates")
    turn_time = relationship("TurnTime", back_populates="rates")
    laboratory = relationship("Laboratory", back_populates="rates")


# Lab Fees Order/Estimation with Staff Assignments
class LabFeesOrder(Base):
    __tablename__ = "lab_fees_orders"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, nullable=True)
    
    # Link to HRS Estimation if applicable
    hrs_estimation_id = Column(Integer, ForeignKey("hrs_estimations.id"), nullable=True)
    
    # Order totals
    total_samples = Column(Float, nullable=False, default=0.0)
    total_lab_fees_cost = Column(Float, nullable=False, default=0.0)
    total_staff_labor_cost = Column(Float, nullable=False, default=0.0)
    total_cost = Column(Float, nullable=False, default=0.0)
    
    # Staff breakdown summary
    staff_breakdown = Column(JSON, nullable=True)  # [{"role": "Env Scientist", "count": 2, "total_hours": 8.0}]
    staff_labor_costs = Column(JSON, nullable=True)  # {"Env Scientist": 744.0, "Env Technician": 289.6}
    
    # Order details snapshot
    order_details = Column(JSON, nullable=True)  # Store test selections and quantities
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    staff_assignments = relationship("LabFeesStaffAssignment", back_populates="order", cascade="all, delete-orphan")


# Staff assignments for lab fees collection
class LabFeesStaffAssignment(Base):
    __tablename__ = "lab_fees_staff_assignments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("lab_fees_orders.id"), nullable=False)
    
    # Staff details
    role = Column(String, nullable=False)  # e.g., "Env Scientist", "Env Technician"
    count = Column(Integer, nullable=False, default=1)  # Number of staff with this role
    hours_per_person = Column(Float, nullable=False, default=0.0)  # Hours each person will work
    total_hours = Column(Float, nullable=False, default=0.0)  # count * hours_per_person
    hourly_rate = Column(Float, nullable=False, default=0.0)  # Rate for this role
    total_cost = Column(Float, nullable=False, default=0.0)  # total_hours * hourly_rate
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    order = relationship("LabFeesOrder", back_populates="staff_assignments")

