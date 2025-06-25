# week07/example-2/backend/order_service/app/models.py

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


class Order(Base):
    __tablename__ = "orders_week07_example_02"

    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    order_date = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status = Column(String(50), nullable=False, default="pending")
    total_amount = Column(Numeric(10, 2), nullable=False)
    shipping_address = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Define a relationship to OrderItem for easy access to order items from an Order object
    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Order(id={self.order_id}, user_id={self.user_id}, status='{self.status}', total={self.total_amount})>"


class OrderItem(Base):
    __tablename__ = "order_items_week07_example_02"

    order_item_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign key to the 'orders' table
    order_id = Column(
        Integer,
        ForeignKey("orders_week07_example_02.order_id"),
        nullable=False,
        index=True,
    )

    product_id = Column(Integer, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price_at_purchase = Column(Numeric(10, 2), nullable=False)
    item_total = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    order = relationship("Order", back_populates="items")

    def __repr__(self):
        return f"<OrderItem(id={self.order_item_id}, order_id={self.order_id}, product_id={self.product_id}, qty={self.quantity})>"
