# week03/example-1/backend/product_service/app/schemas.py

"""
Pydantic schemas for the Product Service API.

These schemas define the data structures for incoming requests (creating and updating products)
and outgoing responses (retrieving product details), ensuring data validation and clear API contracts.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)
    image_url: Optional[str] = Field(None, description="URL of the product image (e.g., from Azure Blob Storage).") # NEW

# Schema for creating a Product (all fields required for creation, except optional ones)
class ProductCreate(ProductBase):
    pass

# Schema for updating a Product (all fields optional for partial update)
class ProductUpdate(ProductBase):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = Field(None)

# Schema for reading/responding with a Product (includes product_id)
class ProductResponse(ProductBase):
    product_id: int
    created_at: datetime # Datetime will be handled as string from DB
    updated_at: Optional[datetime] = None # Datetime will be handled as string from DB

    model_config = ConfigDict(from_attributes=True)