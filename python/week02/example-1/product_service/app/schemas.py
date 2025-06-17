# week02/example-1/product_service/app/schemas.py

"""
Pydantic schemas for the Product Service API.
These define the data structures for incoming requests and outgoing responses,
ensuring data validation and clear API contracts.
"""

from datetime import datetime
from typing import Optional  # Use Optional for fields that might be None

from pydantic import BaseModel, ConfigDict, Field, validator


# Schema for creating a new product.
# Used in POST /products/ endpoint.
class ProductCreate(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the product."
    )
    description: Optional[str] = Field(
        None, max_length=2000, description="Detailed description of the product."
    )
    price: float = Field(
        ..., gt=0, description="Price of the product. Must be greater than 0."
    )
    stock_quantity: int = Field(
        ..., ge=0, description="Current stock quantity. Must be non-negative."
    )


# Schema for updating an existing product.
# All fields are Optional, allowing partial updates (PATCH-like behavior for PUT).
# Used in PUT /products/{product_id} endpoint.
class ProductUpdate(BaseModel):
    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="New name of the product."
    )
    description: Optional[str] = Field(
        None, max_length=2000, description="New detailed description of the product."
    )
    price: Optional[float] = Field(
        None, gt=0, description="New price of the product. Must be greater than 0."
    )
    stock_quantity: Optional[int] = Field(
        None, ge=0, description="New stock quantity. Must be non-negative."
    )


# Schema for representing a product in API responses.
# Inherits fields from ProductCreate and adds database-generated fields.
# Used in GET, POST, PUT responses for /products/ endpoints.
class ProductResponse(ProductCreate):
    product_id: int = Field(..., description="Unique identifier of the product.")
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when the product was created."
    )
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp when the product was last updated."
    )

    model_config = ConfigDict(from_attributes=True)
