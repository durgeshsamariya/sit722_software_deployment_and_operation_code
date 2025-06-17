# week02/example-1/product_service/app/models.py

"""
SQLAlchemy database models for the Product Service.
These classes define the structure of tables in the database.
"""

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from .db import Base  # Import Base from your db.py


class Product(Base):
    """
    SQLAlchemy model for the 'products' table.
    Represents a product with its details and stock quantity.
    """

    # Name of the database table
    __tablename__ = "products_week02_example_01"

    # Primary Key: Unique identifier for each product, auto-incrementing.
    product_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Product name: Required, max 255 chars, indexed for faster lookups.
    name = Column(String(255), nullable=False, index=True)

    # Product description: Optional longer text.
    description = Column(Text, nullable=True)

    # Product price: Required, numeric with 10 total digits and 2 decimal places.
    price = Column(Numeric(10, 2), nullable=False)

    # Stock quantity: Required, integer, defaults to 0 if not provided.
    stock_quantity = Column(Integer, nullable=False, default=0)

    # Timestamps for creation and last update.
    # 'created_at' defaults to current timestamp on creation.
    # 'updated_at' updates to current timestamp on every record update.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        # A helpful representation when debugging
        return f"<Product(id={self.product_id}, name='{self.name}', stock={self.stock_quantity})>"
