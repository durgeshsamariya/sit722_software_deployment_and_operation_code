# backend/order_service/app/models.py

"""
SQLAlchemy ORM models for the Order Service.

This module defines the database schema for orders within the microservice.
It includes the core attributes for an order, such as the product ordered,
quantity, customer details, and essential timestamps for tracking.
Each class defined here maps directly to a table in the PostgreSQL database.
"""

from sqlalchemy import Column, DateTime, Integer, String, func

from db import Base


class Order(Base):
    """
    Represents a customer's order in the system.

    This SQLAlchemy model maps to the 'orders_week03' table in the database.
    It captures essential details about each order transaction.
    """
    # Defines the name of the database table for this model.
    __tablename__ = "orders_week03"

    order_id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True, # Automatically increments for new order records, ensuring uniqueness.
        comment="Unique identifier for the order."
    )
    product_id = Column(
        Integer,
        nullable=False,
        comment="The ID of the product that was ordered. "
                "This typically corresponds to a product_id in the Product Service."
    )
    quantity = Column(
        Integer,
        nullable=False,
        comment="The quantity of the specific product ordered. Must be a positive integer."
    )
    customer_name = Column(
        String(255), # Maximum length for the customer's name.
        nullable=False,
        comment="The name of the customer who placed this order."
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(), # Automatically sets the timestamp when the order record is created (UTC).
        comment="Timestamp indicating when the order record was created."
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(), # Automatically updates the timestamp whenever the order record is modified (UTC).
        comment="Timestamp indicating when the order record was last updated."
    )
