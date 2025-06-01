# app/schemas.py

"""
Pydantic schemas for the Product Service API.

These schemas define the data structures for incoming requests (creating and updating products)
and outgoing responses (retrieving product details), ensuring data validation and clear API contracts.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class ProductCreate(BaseModel):
    """
    Schema for creating a new product.

    Defines the required fields and their validation rules when a client
    submits data to create a product resource via the API.
    """
    name: str = Field(
        ..., # Ellipsis (...) indicates a required field.
        min_length=1,
        max_length=255,
        description="Name of the product. Must be between 1 and 255 characters."
    )
    
    description: Optional[str] = Field(
        None, # Default value of None indicates the field is optional.
        max_length=2000,
        description="Detailed description of the product. Optional, up to 2000 characters."
    )
    
    price: float = Field(
        ...,
        gt=0, # 'gt=0' means "greater than 0". Price must be a positive number.
        description="Price of the product. Must be a positive value."
    )
    
    stock_quantity: int = Field(
        ...,
        ge=0,
        description="Quantity of the product in stock. Must be zero or a positive integer."
    )

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)

class ProductResponse(ProductCreate):
    product_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    image_url: Optional[str] = None

    class Config:
        # This tells Pydantic to read data as an ORM model,
        # allowing it to map database column names to schema fields.
        from_attributes = True # Pydantic v2+ equivalent of orm_mode = True
