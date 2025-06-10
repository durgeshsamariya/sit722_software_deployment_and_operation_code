# week03/example-3/backend/product_service/app/models.py

"""
SQLAlchemy database models for the Product Service.
These classes define the structure of tables in the database.
Updated to include an 'image_url' for product photos.
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime
from sqlalchemy.sql import func
from .db import Base

class Product(Base):
    # Name of the database table
    __tablename__ = "products_week03_part_03"

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

    # URL for the product image, stored in Azure Blob Storage. Optional.
    image_url = Column(String(2048), nullable=True) # URL can be long

    # Timestamps for creation and last update.
    # 'created_at' defaults to current timestamp on creation.
    # 'updated_at' updates to current timestamp on every record update.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        # A helpful representation when debugging
        return f"<Product(id={self.product_id}, name='{self.name}', stock={self.stock_quantity}, image_url='{self.image_url[:30] if self.image_url else 'None'}...')>"

