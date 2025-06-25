# week07/example-2/backend/product_service/app/models.py

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from .db import Base


class Product(Base):
    # Name of the database table
    __tablename__ = "products_week07_example_02"
    product_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    image_url = Column(String(2048), nullable=True)  # URL can be long
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        # A helpful representation when debugging
        return f"<Product(id={self.product_id}, name='{self.name}', stock={self.stock_quantity}, image_url='{self.image_url[:30] if self.image_url else 'None'}...')>"
