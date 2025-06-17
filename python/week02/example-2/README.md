# Week 02 Example 2: Full-Stack Microservice Deployment with Docker Compose

This example builds upon Week 02 Example 1 by introducing a frontend application and deploying the entire stack (Frontend, Product Microservice, and PostgreSQL Database) using Docker Compose. This demonstrates how to manage multi-service applications in a local development environment.

### Components:

- Product Microservice: (Python/FastAPI) - Same as Week 02 Example 1, handles product CRUD operations.
- Frontend: (HTML/JavaScript/Nginx) - A simple web interface to view and add products.
- PostgreSQL Database: (Dockerized) - Stores product data.

## 1. Project Setup

### 1.1. Prerequisites

Before you begin, ensure you have the following installed:

- **Git**: For version control. [[Download](https://git-scm.com)]
- **Docker Desktop** (or Docker Engine): Essential for building and running containers (primarily for the Docker Compose section). [[Download](https://www.docker.com/products/docker-desktop/)]
- **Python 3.10+ and pip**: For local backend development and running tests. [[Download](https://www.python.org/downloads/)]
- **PostgreSQL**: For local database testing when running services natively. [[Download](https://www.postgresql.org/download/)]
- **Node.js & npm/Yarn**: For local frontend development. [[Download](https://nodejs.org/)]

### 1.2. Clone the Repository

First, clone the repository to your local machine:

```bash
git clone https://github.com/durgeshsamariya/sit722_software_deployment_and_operation_code.git
```

- Navigate to the `example-2` directory: Ensure your terminal is in the root `example-2` directory, which contains `docker-compose.yml`, `backend/product_service/`, and `frontend/` folders.

  ```bash
  cd /week02/example-2
  ```

### 1.3. Database Setup (Managed by Docker Compose)

The PostgreSQL database will run as a Docker container, managed entirely by Docker Compose. You do not need a separate local PostgreSQL installation for this example if you run it via Docker Compose.

The `db` service in `docker-compose.yml` is configured to:

- Use the `postgres:15-alpine` image.
- Create a database named `products` with user `postgres` and password `postgres`.

## 2. Local Development (Running Frontend & Backend Natively)

This section details how to run the FastAPI backend and the simple HTML/JavaScript frontend directly on your local machine, connecting to your local PostgreSQL installation.

### 2.1 Backend Setup & Run (Product Microservice)

1. Ensure your local PostgreSQL database is running and the products database exists.
   (Refer to the "1.3. Database Setup" section if you haven't done this already).

2. Navigate to the backend service directory:

   ```bash
   cd backend/product_service
   ```

3. Create and activate a Python virtual environment:

   ```bash
   python3 -m venv venv

   source venv/bin/activate  # On Windows: `.\venv\Scripts\activate`
   ```

4. Install backend dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

5. Start the FastAPI application using Uvicorn:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

- The backend service will be accessible at `http://localhost:8000`.

- API Documentation (Swagger UI): `http://localhost:8000/docs`

- Alternative Docs (ReDoc): `http://localhost:8000/redoc`

Keep this terminal open as the backend server will be running. You may open a new terminal for frontend setup.

### 2.2 Frontend Setup & Run (Simple Web Interface)

The frontend is a simple static HTML/JavaScript application. We'll use a basic HTTP server to serve it.

1. Ensure the backend service is running (as described in 2.1) as the frontend communicates with it.

2. Open new terminal
3. Navigate to the frontend directory:

   ```bash
   cd ../../frontend # From product_service, go up two levels to example-2, then into frontend
   # or if in example-2 root:
   # cd frontend
   ```

4. Install a simple HTTP server (if you don't have one):

   ```bash
   python3 -m http.server 3000
   ```

5. Access the Frontend:
   Open your web browser and go to `http://localhost:3000`. You should see the product catalog interface.

## 3. Running Tests Locally

The backend (`product_service`) includes unit tests that connect to a PostgreSQL database.

1. Ensure your local PostgreSQL database is running and accessible on `localhost:5432` with database `products` (user `postgres`, password `postgres`).

- Important: The products database must exist. The setup_database_for_tests fixture in backend/product_service/tests/test_main.py will handle ensuring the products_week02_part_02 table is created (and cleaned) within that database.

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
   pip install -r requirements-dev.txt
   ```

5. Run Pytest:

   ```bash
   pytest tests/
   ```

Pytest will automatically discover and run tests in the `tests/` directory. You should see output indicating the test results (e.g., how many tests passed).

6. Navigate back to the example-2 root directory after tests:

   ```bash
   deactivate # Deactivate virtual environment
   cd ../..
   ```

## 4. Docker Compose Deployment

This single command will build the Docker images for the `product_service` and `frontend`, and then start all three services (`db`, `product_service`, `frontend`) in the correct order.

1. Ensure you are in the `example-2` directory.

2. Build the services:

   ```bash
   docker compose build --no-cache
   ```

3. Start the services:

   ```bash
    docker compose up -d
   ```

4. Verify services are running (optional):

   ```bash
   docker compose ps
   ```

   You should see `db`, `product_service`, and `frontend` listed with up status.

5. Access the applications:

   - Frontend (Product Catalog): Open your web browser and go to `http://localhost:3000`

   - Backend API (Swagger UI): Open your web browser and go to `http://localhost:8000/docs`

   You can now interact with the frontend to add and view products. The frontend will communicate with the backend API, which in turn communicates with the PostgreSQL database, all running within Docker containers.

## 5. Cleaning Up

To stop and remove all services and their associated Docker resources (containers), run:

```bash
docker compose down
```

This will stop the `db`, `product_service`, and `frontend` containers.
