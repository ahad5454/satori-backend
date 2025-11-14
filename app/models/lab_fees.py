from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
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
    sample_count = Column(Float, nullable=True)  # <-- NEW FIELD

    # Relationships
    test = relationship("Test", back_populates="rates")
    turn_time = relationship("TurnTime", back_populates="rates")
    laboratory = relationship("Laboratory", back_populates="rates")

