# Week 02 - Example - 1

## Product Service – Mini E-commerce

This is the Product microservice, a core component of our mini e-commerce application. It's built with FastAPI (a modern, fast Python web framework) and uses PostgreSQL as its robust relational database.

In this module, you'll gain hands-on experience deploying and interacting with a contemporary Python web service using Docker and Docker Compose, and understanding its REST API endpoints.

## 1. Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- Git: For version controle. [[Download](https://git-scm.com)]
- Docker Desktop (or Docker Engine): Essential for building and running containers. [[Download](https://www.docker.com/products/docker-desktop/)]
- Python 3.10+ and pip: For local development and running tests outside Docker. [[Download](https://www.python.org/downloads/)]
- Postgres: For local database testing. [[Download](https://www.postgresql.org/download/)]

### 1.1 Clone the Repository

First, clone the repository to your local machine and navigate to the product service directory:

```bash
git clone https://github.com/durgeshsamariya/sit722_software_deployment_and_operation_code.git
```

### 1.2. Database Setup (Important!)

Before running the service, you must manually create the PostgreSQL database that the application will connect to. The application itself will create the necessary tables within this database on startup, but not the database itself.

- Ensure PostgreSQL is running.
- Connect to your PostgreSQL server (e.g., using psql, pgAdmin, or your preferred SQL client):

```sql
psql -h localhost -p 5432 -U postgres
```

- Create the database:

```sql
CREATE DATABASE products;
```

## 2. Local Development

### 2.1. Install Dependencies

For local development and running tests, you'll need both production and development dependencies. It's recommended to use a Python virtual environment.

```python
# Create and activate a virtual environment
python -m venv venv

source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install all dependencies
pip install -r requirements-dev.txt
```

### 2.2. Run Microservice Locally

This method runs the FastAPI application directly on your local machine, connecting to your locally installed and running PostgreSQL database.

1. Ensure your PostgreSQL database is running and the products database exists.
   (Refer to the "1.2. Database Setup" section if you haven't done this already.)
2. Navigate to the product service directory:

```bash
cd week02/example-1/product_service
```

3. Start the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- `app.main:app`: Specifies that app is the FastAPI application instance within main.py.
- `--host 0.0.0.0`: Makes the application accessible from any network interface (useful for Docker, or if you need to access from another device on your local network).
- `--port 8000`: Sets the port the application listens on.
- `--reload`: Enables auto-reloading of the server when code changes are detected (useful for development).

4. Access the API Documentation:

Once the server starts, you can access the API documentation (Swagger UI) in your browser:

API Documentation (Swagger UI): `http://localhost:8000/docs`

Alternative Docs (ReDoc): `http://localhost:8000/redoc`

Use the `/docs` page to interact with the API directly in your browser.

### Run Pytests

Before running the service, you can execute the unit and integration tests to ensure everything is working as expected.

1. Navigate to the product service directory:

```bash
cd week02/example-1/product_service
```

2.Activate your Python virtual environment (if not already active):

```bash
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Run the tests using Pytest:

```bash
pytest tests
```

### 2.3. Run with Docker

This is the recommended way to run the service and its database for local development.

1. Navigate to the product_service folder if you're not already there:

```bash
cd week02/example-1/product_service
```

2. Build and start the containers:

```bash
docker build --no-cache -t week02_product_service .

docker run -d -p 8000:8000 week02_product_serivce
```

3. The FastAPI service will be available at:

- API Documentation (Swagger UI): `http://localhost:8000/docs`
- Alternative Docs (ReDoc): `http://localhost:8000/redoc`

Use the /docs page to interact with the API directly in your browser.

## 3. Example Endpoints

You can use the `/docs` page to try out the API, or tools like Postman or curl.

- List all products:
  `GET /products/`

- Create a new product:
  `POST /products/`

- Update stock quantity:
  `PUT /products/{product_id}/stock`

- Get, update, delete by ID:
  `GET /products/{id}, PUT /products/{id}, DELETE /products/{id}`
