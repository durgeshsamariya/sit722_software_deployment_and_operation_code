# backend/order_service/app/models.py

"""
SQLAlchemy models for Order Service.
Includes customer_id and order status for asynchronous flow.
"""

from sqlalchemy import Column, DateTime, Integer, String, func, Text
from sqlalchemy import Enum as SQLEnum
import enum
import json

from db import Base

# Define an Enum for order status
class OrderStatus(enum.Enum):
    PENDING_STOCK_CHECK = "pending_stock_check"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Order(Base):
    __tablename__ = "orders_week04"

    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    #product_id = Column(Integer, nullable=False)
    #quantity = Column(Integer, nullable=False)
    items_json = Column(Text, nullable=False)
    #customer_name = Column(String(255), nullable=False)
    status = Column(
        SQLEnum(OrderStatus),
        nullable=False,
        default=OrderStatus.PENDING_STOCK_CHECK,
        index=True
    ) # New: Order status for async flow
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
