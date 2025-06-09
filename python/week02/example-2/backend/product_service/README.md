# Product Service

# Product Service – Mini E-commerce Example

This is the Product microservice, a core component of our mini e-commerce application. It's built with FastAPI (a modern, fast Python web framework) and uses PostgreSQL as its robust relational database.

In this module, you'll gain hands-on experience deploying and interacting with a contemporary Python web service using Docker and Docker Compose, and understanding its REST API endpoints.

---

## 1. Project Structure

week02/backend/product_service/
├── app/
│   ├── main.py        # FastAPI application entry point and API endpoints.
│   ├── db.py          # Database configuration, SQLAlchemy engine, and session management.
│   ├── models.py      # SQLAlchemy ORM models, defining the database table schema (e.g., Product).
│   └── schemas.py     # Pydantic schemas for data validation (request bodies) and response serialization.
├── tests/
│   └── test_main.py   # Pytest integration tests for the API endpoints.
├── requirements.txt   # Production Python dependencies required to run the application.
├── requirements-dev.txt # Development and testing Python dependencies (e.g., pytest, httpx).
└── Dockerfile         # Instructions for building the Docker image for the Product Service.


## 2. Getting Started
Prerequisites

Before you begin, ensure you have the following installed:

- Git: For cloning the repository.
- Docker Desktop (or Docker Engine): Essential for building and running containers.
- Python 3.10+ and pip: For local development and running tests outside Docker.


### 2.1 Clone the Repository

First, clone the repository to your local machine and navigate to the product service directory:

### 2.2. Database Setup (Important!)

Before running the service, you must manually create the PostgreSQL database that the application will connect to. The application itself will create the necessary tables within this database on startup, but not the database itself.

- Ensure PostgreSQL is running.
- Connect to your PostgreSQL server (e.g., using psql, pgAdmin, or your preferred SQL client):

```
psql -h localhost -p 5432 -U postgres
```

- Create the database:
```
CREATE DATABASE products;
```

## 3. Local Development

### 3.1. Install Dependencies

For local development and running tests, you'll need both production and development dependencies. It's recommended to use a Python virtual environment.
```
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt -r requirements-dev.txt
```
### 3.2. Run with Docker Compose

This is the recommended way to run the service and its database for local development, as it handles the database container setup automatically.

1. Navigate to the product_service folder if you're not already there:
```
cd week02/backend/product_service
```

2. Build and start the containers:
```
docker build -t week02_product_service .
docker run -d -p 8000:8000 week02_product_serivce
```

3. The FastAPI service will be available at:
- API Documentation (Swagger UI): http://localhost:8000/docs
- Alternative Docs (ReDoc): http://localhost:8000/redoc

Use the /docs page to interact with the API directly in your browser.

## 4. Example Endpoints

You can use the /docs page to try out the API, or tools like Postman or curl.

- List all products:
`GET /products/`
- Create a new product:
`POST /products/`
- Update stock quantity:
`PUT /products/{product_id}/stock`
- Get, update, delete by ID:
`GET /products/{id}, PUT /products/{id}, DELETE /products/{id}`

