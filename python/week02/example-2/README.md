# Week 02 Example 2: Full-Stack Microservice Deployment with Docker Compose

This example builds upon Week 02 Example 1 by introducing a frontend application and deploying the entire stack (Frontend, Product Microservice, and PostgreSQL Database) using Docker Compose. This demonstrates how to manage multi-service applications in a local development environment.

### Components:

- Product Microservice: (Python/FastAPI) - Same as Week 02 Example 1, handles product CRUD operations.
- Frontend: (HTML/JavaScript/Nginx) - A simple web interface to view and add products.
- PostgreSQL Database: (Dockerized) - Stores product data.

---

## 1. Getting Started

Follow these steps to set up, build, and run the entire application stack using Docker Compose.


* **Prerequisites:**
Before you begin, ensure you have the following installed on your machine:

1. Docker Desktop: (Includes Docker Engine, CLI, and Docker Compose)
- Download from: https://www.docker.com/products/docker-desktop/
2. Python 3.10+: (Only needed for backend development and running backend tests directly on host)
- Download from: https://www.python.org/downloads/

---

## 2. Project Setup

- Navigate to the example-2 directory: Ensure your terminal is in the root `example-2` directory, which contains `docker-compose.yml`, `backend/product_service/`, and `frontend/` folders.

```bash
cd your_project_folder/week02/example-2
```

- Database Setup (Managed by Docker Compose)

The PostgreSQL database will run as a Docker container, managed entirely by Docker Compose. You do not need a separate local PostgreSQL installation for this example if you run it via Docker Compose.

The `db` service in `docker-compose.yml` is configured to:

- Use the `postgres:15-alpine` image.
- Create a database named `products` with user `postgres` and password `postgres`.

---

## 3. Running the Entire Stack with Docker Compose

This single command will build the Docker images for the product_service and frontend, and then start all three services (db, product_service, frontend) in the correct order.

1. Ensure you are in the example-2 directory.

2. Build and start the services:
```bash
docker compose up --build -d
```
- `--build`: Forces a rebuild of images, useful if you've made code changes.
- `-d`: Runs the containers in detached mode (in the background).

3. Verify services are running (optional):
```bash
docker compose ps
```

You should see `db`, `product_service`, and `frontend` listed with Up status.

4. Access the applications:

- Frontend (Product Catalog): Open your web browser and go to `http://localhost:3000`
- Backend API (Swagger UI): Open your web browser and go to `http://localhost:8000/docs`

You can now interact with the frontend to add and view products. The frontend will communicate with the backend API, which in turn communicates with the PostgreSQL database, all running within Docker containers.

---

## 4.  Running Backend Unit Tests

The backend (`product_service`) includes unit/integration tests that connect to a PostgreSQL database. To run these tests:

1. Ensure your local PostgreSQL database is running and accessible on `localhost:5432` with database `products`, user `postgres`, and password `postgres`.

    - Important: The products database must exist. The `setup_database_for_tests` fixture in `backend/product_service/tests/test_main.py` will handle ensuring the `products_week02_part_02` table is created within that database. It also ensures a clean state by dropping and recreating tables at the start of the test session. You can use the docker run command provided in the "Database Setup" section if you prefer to use a Docker container for this.

2. Navigate into the product_service directory:
```bash
cd backend/product_service
```

3. Create and activate a Python virtual environment (if you haven't already):

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

4. Install backend dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

5. Run Pytest:
```bash
pytest tests/
```

Pytest will automatically discover and run tests in the tests/ directory. You should see output indicating the test results (e.g., how many tests passed).

6. Navigate back to the `example-2` root directory:


```bash
cd ../..
```
---

## 5. Cleaning Up

To stop and remove all services and their associated Docker resources (containers), run:

```bash
docker compose down
```

This will stop the `db`, `product_service`, and `frontend` containers.
