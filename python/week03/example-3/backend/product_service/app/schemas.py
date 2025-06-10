# week03/example-3/backend/product_service/app/schemas.py

from typing import Optional
from datetime import datetime # Import datetime for ProductResponse
from pydantic import BaseModel, Field, ConfigDict

# Base schema for Product
class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)
    image_url: Optional[str] = Field(None, max_length=2048, description="URL of the product image (e.g., from Azure Blob Storage).")

# Schema for creating a Product (all fields required for creation, except optional ones)
class ProductCreate(ProductBase):
    pass

# Schema for updating a Product (all fields optional for partial update)
class ProductUpdate(ProductBase):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = Field(None, max_length=2048)

# Schema for reading/responding with a Product (includes product_id)
class ProductResponse(ProductBase):
    product_id: int
    created_at: datetime # Datetime type for Pydantic to serialize
    updated_at: Optional[datetime] = None # Datetime type for Pydantic to serialize

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode for Pydantic V2


# Schema for stock deduction request
class StockDeductRequest(BaseModel):
    """
    Schema for requesting a stock deduction.
    """
    quantity_to_deduct: int = Field(..., gt=0, description="Quantity of product to deduct from stock.")