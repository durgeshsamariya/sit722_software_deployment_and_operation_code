# app/models.py


"""
SQLAlchemy models for the Product Service.

This module defines the database schema for products, including their
attributes and relationships (though no relationships are defined yet).
Each class represents a table in the PostgreSQL database.
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime
from sqlalchemy.sql import func
from db import Base

class Product(Base):
    # Table name for this model in the database.
    __tablename__ = "products_week03"

    product_id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="Unique identifier for the product."
    )
    
    name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Name of the product. Must be unique and not null."
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Detailed description of the product. Can be null."
    )
    
    price = Column(
        Numeric(10, 2),
        nullable=False, 
        comment="Price of the product. Must be a positive value."
    )
    
    stock_quantity = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Current stock quantity of the product. Cannot be null, defaults to 0."
    )
    
    image_url = Column(
        String,
        nullable=True,
        comment="URL of the product image. Can be null if no image is provided."
    )
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(), # Automatically sets the creation timestamp upon record insertion.
        comment="Timestamp when the product record was created (UTC)."
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(), # Automatically updates the timestamp when the record is modified.
        comment="Timestamp when the product record was last updated (UTC)."
    )
