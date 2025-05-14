# db.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import time

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@order-db:5432/orders"

# Retry logic for DB health
while True:
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        break
    except Exception:
        print("Waiting for DB to be ready...")
        time.sleep(2)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
