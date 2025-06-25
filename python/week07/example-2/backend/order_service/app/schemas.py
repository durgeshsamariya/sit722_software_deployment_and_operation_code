# week07/example-2/backend/order_service/app/schemas.py

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OrderItemBase(BaseModel):
    product_id: int = Field(
        ..., ge=1, description="ID of the product from the Product Service."
    )
    quantity: int = Field(..., ge=1, description="Quantity of the product ordered.")
    price_at_purchase: float = Field(
        ..., gt=0, description="Price of the product at the time of purchase."
    )


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    order_item_id: int
    order_id: int  # The ID of the parent order
    item_total: float  # Calculated total for this specific item
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)  # Enable ORM mode for Pydantic V2


class OrderBase(BaseModel):
    user_id: int = Field(..., ge=1, description="ID of the user placing the order.")
    shipping_address: Optional[str] = Field(
        None, max_length=1000, description="Shipping address for the order."
    )
    status: Optional[str] = Field(
        "pending",
        max_length=50,
        description="Current status of the order (e.g., pending, processing, shipped).",
    )


class OrderCreate(OrderBase):
    items: List[OrderItemCreate] = Field(
        ..., min_length=1, description="List of items in the order."
    )


class OrderUpdate(OrderBase):
    user_id: Optional[int] = Field(None, ge=1)


class OrderResponse(OrderBase):
    order_id: int
    order_date: datetime
    total_amount: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []  # Nested items for detailed order response

    model_config = ConfigDict(from_attributes=True)  # Enable ORM mode for Pydantic V2
