# week2/backend/product_service/app/main.py

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String
from pydantic import BaseModel
from .db import engine, Base, get_db


# -----------------------------
# Models
# -----------------------------
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, index=True)


Base.metadata.create_all(bind=engine)


# -----------------------------
# Schemas
# -----------------------------
class ProductCreate(BaseModel):
    name: str
    description: str


class ProductUpdate(BaseModel):
    name: str
    description: str


class ProductResponse(ProductCreate):
    id: int

    class Config:
        orm_mode = True


# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only — use specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create
@app.post("/products/", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(name=product.name, description=product.description)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


# Read All
@app.get("/products/", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


# Read One
@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# Update
@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int, updated: ProductUpdate, db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.name = updated.name
    product.description = updated.description
    db.commit()
    db.refresh(product)
    return product


# Delete
@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"detail": "Product deleted successfully"}
