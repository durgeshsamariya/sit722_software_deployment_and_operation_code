# Week 03 Example 1: Full-Stack Microservices with Dedicated Databases, Persistent Storage & Azure Blob Storage

This example significantly expands on previous weeks by demonstrating a more robust microservices architecture. It features two distinct microservices, each with its own dedicated PostgreSQL database, a unified frontend, and integration with Azure Blob Storage for handling product images. All components are orchestrated using Docker Compose, emphasizing persistent storage for the databases.

### Components
- Product Microservice: (Python/FastAPI)
    - Manages product information.
    - Integrates with Azure Blob Storage for product image uploads, generating Shared Access Signature (SAS) URLs for secure access to images.
    - Connects to its dedicated product_db PostgreSQL instance.
- Order Microservice: (Python/FastAPI)
    - Manages customer orders and their individual items.
    - Connects to its dedicated `order_db` PostgreSQL instance.
- Frontend: (HTML/JavaScript/Nginx)
    - A simple web interface that allows users to:
        - Create and view products (including uploading images to Azure).
        - Add products to a shopping cart.
        - Place new orders.
        - View all placed orders and update their status.
- PostgreSQL Databases (2 instances): (Dockerized)
    - `product_db`: Dedicated for the Product Service.
    - `order_db`: Dedicated for the Order Service.
    - Both databases use Docker volumes for persistent storage, ensuring data is retained across container restarts.

## Getting Started

Follow these steps to set up, build, and run the entire application stack using Docker Compose.

#### Prerequisites

Before you begin, ensure you have the following installed on your machine:

1. Docker Desktop: (Includes Docker Engine, CLI, and Docker Compose)
    - Download from: https://www.docker.com/products/docker-desktop/

2. Python 3.10+: (Only needed for backend local development and running backend tests directly on the host)
    - Download from: https://www.python.org/downloads/

3. Azure Storage Account:

    - You will need an Azure Storage account with a Blob Storage container created.
    - Get your Account Name and Account Key (from "Access keys" under "Security + networking" in your Storage Account blade).
    - Create a Blob Container (e.g., named product-images). This container does not need to be public; the application will generate SAS tokens for access.

## 1. Project Setup

1. Navigate to the `example-1` directory: Ensure your terminal is in the root `week03/example-1` directory, which contains `docker-compose.yml`, `backend/`, and `frontend/` folders.

```bash
cd your_project_folder/week03/example-1
```

## 2. Configure Azure Storage Credentials

The `product_service` needs your Azure Storage credentials to upload images. These will be passed as environment variables to the Docker container via `docker-compose.yml`.

Change the following values in `docker-compose.yml` file.

```bash
# week03/example-1/.env
AZURE_STORAGE_ACCOUNT_NAME=your_azure_storage_account_name
AZURE_STORAGE_ACCOUNT_KEY=your_azure_storage_account_key
AZURE_STORAGE_CONTAINER_NAME=product-images # Or whatever you named your container
AZURE_SAS_TOKEN_EXPIRY_HOURS=24 # e.g., 24 or 48 hours for SAS token validity
```

**Important: Replace your_azure_storage_account_name and your_azure_storage_account_key with your actual Azure Storage credentials.**

## 3. Database Setup (Managed by Docker Compose with Persistence)

Both PostgreSQL databases (`product_db` and `order_db`) will run as Docker containers, managed entirely by Docker Compose. You do not need separate local PostgreSQL installations for this example.

The `docker-compose.yml` file is configured to:

- Use postgres:15-alpine images for both databases.
- Create databases named `products` and `orders` respectively, with user `postgres` and password `postgres`.
- Crucially, persistent named volumes (`product_db_data` and `order_db_data`) are mounted to `/var/lib/postgresql/data` inside each container. This ensures that any data you add to your databases will persist even if you stop, remove, and recreate the containers.

## 4. Building and Running the Entire Stack with Docker Compose

This single command will build the Docker images for the `product_service`, `order_service`, and `frontend`, and then start all five services (`product_db`, `order_db`, `product_service`, `order_service`, `frontend`) in the correct order.

1. Ensure you are in the `week03/example-2` directory.

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

You should see `product_db_container`, `order_db_container`, `product_api_container`, `order_api_container`, and `product_order_frontend` listed with Up status.

4. Access the applications:

- Frontend Application: Open your web browser and go to http://localhost:3000
- Product Service API (Swagger UI): Open your web browser and go to http://localhost:8000/docs
- Order Service API (Swagger UI): Open your web browser and go to http://localhost:8001/docs

You can now interact with the frontend to add products (including images), place orders, and view order details.

5. Persistent Storage in Action

The `docker-compose.yml` explicitly defines named volumes: `product_db_data` and `order_db_data`.

- These volumes are managed by Docker and store the actual PostgreSQL database files on your host machine in a location managed by Docker.

- To demonstrate persistence:

    1. Add some products and orders via the frontend.
    2. Stop the services: `docker compose down`.
    3. Start the services again: docker compose up -d.
    4. Access the frontend (http://localhost:3000) - your previously added data should still be there!

- To delete the persistent data (e.g., for a clean start), you must explicitly remove the volumes:

```bash
docker compose down --volumes
```
**Use this if you want a completely fresh start for the databases.**

## 6. Running Backend Tests
To run the unit/integration tests for each backend microservice:

1. Ensure the respective service container is running (e.g., product_api_container for product tests, order_api_container for order tests) via docker compose up -d.

2. Run Product Service Tests:

```bash
docker compose exec product_api_container pytest tests/
```

This command runs pytest within the running product_api_container, targeting its tests/ directory.

3. Run Order Service Tests:

```bash
docker compose exec order_api_container pytest tests/
```

This command runs pytest within the running order_api_container, targeting its tests/ directory.

## 7. Stopping the Services

To stop and remove the Docker containers and networks created by Docker Compose:

1. Navigate to the `week03/example-2` root directory:
```bash
cd <REPO_ROOT>/week03/example-2
```

2. Stop services:
```bash
docker compose stop
```

3. Stop and remove services (including networks, but preserving volumes):
```bash
docker compose down
```

This is the most common way to shut down.

4. Stop, remove services, and remove persistent volumes (for a clean slate):
```bash
docker compose down --volumes
```