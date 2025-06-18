# week04/example-3/backend/customer_service/app/models.py

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func  # For auto-populating timestamps

from .db import Base


class Customer(Base):
    __tablename__ = "customers_week04_example_03"

    customer_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)  # Stores the hashed password
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone_number = Column(String, index=True)
    shipping_address = Column(String)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        """
        String representation of the Customer object, useful for debugging.
        """
        return f"<Customer(id={self.customer_id}, email='{self.email}', name='{self.first_name} {self.last_name}')>"
