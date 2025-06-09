# Week 02 Example 1: Product Microservice with Local Docker Deployment

This example demonstrates a single **Product Microservice** built with FastAPI and PostgreSQL, running in a Docker container. The primary goal of this example is to cover fundamental **Docker** concepts: building an image and running a container.

For simplicity in this initial example:
- **Only the Product Service** is included.
- The database is a **local PostgreSQL instance** (outside of Docker for this service).
- **All configurations are hardcoded** directly in the code (e.g., database credentials and database host as `localhost`), to avoid introducing environment variables or Secrets/ConfigMaps in Week 02.
- The service runs in a **single Docker container**; Docker Compose is *not* used in this example.

---

## 🚀 Getting Started

Follow these steps to get the Product Microservice running locally and then inside a Docker container.

### Prerequisites

Before you begin, ensure you have the following installed on your machine:

1.  **Docker Desktop:** (Includes Docker Engine, CLI, and Docker Compose)
    * Download from: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
2.  **Python 3.10+:**
    * Download from: [https://www.python.org/downloads/](https://www.python.org/downloads/)
3.  **PostgreSQL Database:**
    * You need a local PostgreSQL server instance.
    * **Recommended:** Install PostgreSQL directly on your machine (e.g., via Homebrew for macOS, apt for Linux, or a standalone installer for Windows).
    * **Alternative (using Docker for DB only):** If you prefer not to install PostgreSQL directly, you can run a PostgreSQL container temporarily:
        ```bash
        docker run --name local-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=products -p 5432:5432 -d postgres:15-alpine
        ```
        Remember to stop/remove it when done: `docker stop local-postgres && docker rm local-postgres`

### 1. Project Setup

1.  **Navigate to the `product_service` directory:**
    If you've cloned a repository, make sure your terminal is in the `product_service` directory which contains the `app` folder, `Dockerfile`, and `requirements.txt`.
    ```bash
    cd your_project_folder/product_service
    ```

2.  **Create a Python Virtual Environment** (optional, but recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 2. Database Setup

The Product Service expects a PostgreSQL database named `products` with user `postgres` and password `postgres`.

1.  **Start your local PostgreSQL server.**
2.  **Create the `products` database:**
    Open your PostgreSQL client (like `psql` in your terminal or a GUI like pgAdmin) and run the following command:
    ```sql
    CREATE DATABASE products;
    ```
    (If you used the Docker command to run PostgreSQL locally, this database will be created automatically by the `postgres:15-alpine` image due to the `POSTGRES_DB` environment variable.)

### 3. Running the Product Service (Locally - Python Only)

This step runs the service directly from Python, without Docker, to confirm basic functionality and database connection.

1.  **Ensure your virtual environment is active** and dependencies are installed.
2. **Navigate into the `app` directory:**
    ```bash
    cd app
    ```
3.  **Run the FastAPI application:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```
    You should see output indicating Uvicorn has started and is listening on `http://0.0.0.0:8000`.

4.  **Test the service:**
    Open your browser to `http://localhost:8000/docs` to see the OpenAPI (Swagger UI) documentation.
    You can also test the new root endpoint:
    ```bash
    curl http://localhost:8000/
    ```
    Expected output: `{"message":"Welcome to the Product Service!"}`

    And the health endpoint:
    ```bash
    curl http://localhost:8000/health
    ```
    Expected output: `{"status":"ok","service":"product-service"}`

5.  **Stop the service:** Press `CTRL+C` in your terminal.

6. **Navigate back to the `product_service` directory:**
    ```bash
    cd ..
    ```

### 4. Running the Product Service (Using Docker)

Now, let's build a Docker image for the service and run it in a container.

1.  **Ensure you are in the `product_service` directory.**
2.  **Build the Docker image:**
    This command reads the `Dockerfile` and builds a Docker image named `product-service-week02:latest`.
    ```bash
    docker build -t product-service-week02:latest .
    ```
    You should see output indicating a successful build.

3.  **Run the Docker container:**
    This command runs a container from your newly built image and maps port 8000 from the container to port 8000 on your host machine.
    ```bash
    docker run -p 8000:8000 --name product-service-container -e POSTGRES_HOST=host.docker.internal product-service-week02:latest
    ```
    * `-p 8000:8000`: Maps host port 8000 to container port 8000.
    * `--name product-service-container`: Assigns a name to your container for easy management.
    * `-e DB_HOST=host.docker.internal`: Sets the `DB_HOST` environment variable inside the container. `host.docker.internal` is a special DNS name that resolves to your host machine's IP address when using Docker Desktop (macOS/Windows).
    * `product-service-week02:latest`: The name and tag of the image to use.

    You should see the Uvicorn server logs directly in your terminal, similar to when running locally.

4.  **Test the service (running in Docker):**
    Open your browser to `http://localhost:8000/docs` to verify it's working.
    Test the root endpoint:
    ```bash
    curl http://localhost:8000/
    ```
    Expected output: `{"message":"Welcome to the Product Service!"}`
    Test the health endpoint:
    ```bash
    curl http://localhost:8000/health
    ```
    Expected output: `{"status":"ok","service":"product-service"}`

5.  **Stop and remove the container:**
    In a **new terminal window** (keep the one running the container open for now), you can list running containers:
    ```bash
    docker ps
    ```
    Find your `product-service-container`. Then stop it:
    ```bash
    docker stop product-service-container
    ```
    The logs in your original terminal (where you ran `docker run`) should now show Uvicorn shutting down.
    Finally, remove the container (you can't run a new container with the same name if an old one exists, even if stopped):
    ```bash
    docker rm product-service-container
    ```

### 5. Running Tests
This section covers how to run the automated tests for your Product Service. These tests require a local PostgreSQL database running on your host machine.

1.  **Ensure you are in the `product_service` directory.**
2.  **Ensure your Python virtual environment is active** and both `requirements.txt` and `requirements-dev.txt` dependencies are installed.
3.  **Start your local PostgreSQL server.**
    The tests will connect to `localhost:5432` with user `postgres`, password `postgres`, and database `products`. This is the *same* database setup you use for local development. The test suite uses transactions to ensure each test runs in isolation without affecting the main database data.
    If you're using the Docker command for your local development DB, ensure it's running:
    ```bash
    docker run --name local-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=products -p 5432:5432 -d postgres:15-alpine
    ```
    **Important:** The `products` database must exist. The `setup_database_for_tests` fixture in `test_main.py` will handle ensuring the `products_week04_part_02` table is created within that database.

4.  **Run Pytest:**
    ```bash
    pytest tests/
    ```
    Pytest will automatically discover and run tests in the `tests/` directory. You should see output indicating the test results (e.g., how many tests passed).

5.  **Stop and remove the local PostgreSQL container (if you used Docker for it):**
    ```bash
    docker stop local-postgres
    docker rm local-postgres
    ```

### 6. Testing the API Endpoints (Manual API Calls)

Once the service is running (either locally or in Docker), you can interact with its API.

#### Create a Product (POST /products/)

```bash
curl -X POST \
  http://localhost:8000/products/ \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Laptop Pro X",
    "description": "High-performance laptop for professionals.",
    "price": 1200.00,
    "stock_quantity": 50
  }'
```

#### List All Products (GET /products/)

```bash
curl http://localhost:8000/products/
```

#### Get Product by ID (GET /products/{product_id})

```bash
curl http://localhost:8000/products/1
```

#### Update a Product (PUT /products/{product_id})

```bash
curl -X PUT \
  http://localhost:8000/products/1 \
  -H 'Content-Type: application/json' \
  -d '{
    "price": 1150.00,
    "stock_quantity": 45
  }'
```

#### Delete a Product (DELETE /products/{product_id})

```bash
curl -X DELETE http://localhost:8000/products/1
```