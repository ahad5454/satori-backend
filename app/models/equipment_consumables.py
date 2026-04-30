from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class EquipmentCategory(Base):
    __tablename__ = "equipment_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    section = Column(Integer, nullable=False)  # 1 for Consumables, 2 for Equipment

    # Relationships
    items = relationship("EquipmentItem", back_populates="category", cascade="all, delete-orphan")


class EquipmentItem(Base):
    __tablename__ = "equipment_items"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("equipment_categories.id"), nullable=False)
    description = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    unit_cost = Column(Float, nullable=False)

    # Relationships
    category = relationship("EquipmentCategory", back_populates="items")


class EquipmentOrder(Base):
    __tablename__ = "equipment_orders"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, nullable=True)
    
    section_1_total = Column(Float, nullable=False, default=0.0)
    section_2_total = Column(Float, nullable=False, default=0.0)
    total_cost = Column(Float, nullable=False, default=0.0)
    
    order_details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
