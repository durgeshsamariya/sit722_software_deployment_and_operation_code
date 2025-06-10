# week03/example-1/backend/order_service/app/models.py

"""
SQLAlchemy ORM models for the Order Service.

This module defines the database schema for orders within the microservice.
It includes the core attributes for an order, such as the product ordered,
quantity, customer details, and essential timestamps for tracking.
Each class defined here maps directly to a table in the PostgreSQL database.
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .db import Base


class Order(Base):
    """
    Represents a customer's order in the system.

    This SQLAlchemy model maps to the 'orders_week03' table in the database.
    It captures essential details about each order transaction.
    """
    # Defines the name of the database table for this model.
    __tablename__ = "orders_week03_part_03"

    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True) # Placeholder for user, not a real FK
    order_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(50), nullable=False, default="pending") # e.g., 'pending', 'processing', 'shipped', 'cancelled'
    total_amount = Column(Numeric(10, 2), nullable=False)
    shipping_address = Column(Text, nullable=True) # Full shipping address text

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Define a relationship to OrderItem for easy access to order items from an Order object
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.order_id}, user_id={self.user_id}, status='{self.status}', total={self.total_amount})>"

class OrderItem(Base):
    """
    SQLAlchemy model for the 'order_items' table.
    Represents an individual product within an order.
    """
    __tablename__ = "order_items_week03_part_03" # Unique table name for this example

    order_item_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign key to the 'orders' table
    order_id = Column(Integer, ForeignKey("orders_week03_part_03.order_id"), nullable=False, index=True)
    
    product_id = Column(Integer, nullable=False, index=True) # Logical link to Product Service's product
    quantity = Column(Integer, nullable=False)
    price_at_purchase = Column(Numeric(10, 2), nullable=False) # Price at the time of order
    item_total = Column(Numeric(10, 2), nullable=False) # Calculated total for this item

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Define a relationship back to Order
    order = relationship("Order", back_populates="items")

    def __repr__(self):
        return f"<OrderItem(id={self.order_item_id}, order_id={self.order_id}, product_id={self.product_id}, qty={self.quantity})>"
