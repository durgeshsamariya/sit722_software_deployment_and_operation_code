# week07/example-2/backend/product_service/app/schemas.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)
    image_url: Optional[str] = Field(
        None,
        max_length=2048,
        description="URL of the product image (e.g., from Azure Blob Storage).",
    )


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = Field(None, max_length=2048)


class ProductResponse(ProductBase):
    product_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockDeductRequest(BaseModel):
    quantity_to_deduct: int = Field(
        ..., gt=0, description="Quantity of product to deduct from stock."
    )
