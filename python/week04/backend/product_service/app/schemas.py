# app/schemas.py

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)

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
        orm_mode = True
