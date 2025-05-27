# backend/order_service/app/models.py

"""
SQLAlchemy models for Order Service.
"""

from sqlalchemy import Column, DateTime, Integer, String, func

from db import Base


class Order(Base):
    __tablename__ = "orders_week03"

    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    customer_name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
