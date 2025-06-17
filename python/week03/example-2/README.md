# Week 03 Example 2: Full-Stack Microservices with Dedicated Databases, Persistent Storage & Azure Blob Storage

This example significantly expands on previous weeks by demonstrating a more robust microservices architecture. It features two distinct microservices, each with its own dedicated PostgreSQL database, a unified frontend, and integration with Azure Blob Storage for handling product images. All components are orchestrated using Docker Compose, emphasizing persistent storage for the databases.

## Getting Started

Follow these steps to set up, build, and run the entire application stack using Docker Compose.

#### Prerequisites

1. Azure Storage Account:

   - You will need an Azure Storage account with a Blob Storage container created.
   - Get your Account Name and Account Key (from "Access keys" under "Security + networking" in your Storage Account blade).
   - Create a Blob Container (e.g., named product-images). This container does not need to be public; the application will generate SAS tokens for access.

## 1. Project Setup

Navigate to the `example-2` directory: Ensure your terminal is in the root `week03/example-1` directory, which contains `docker-compose.yml`, `backend/`, and `frontend/` folders.

```bash
cd <your_project_folder>/week03/example-2
```

## 2. Configure Azure Storage Credentials

The `product_service` needs your Azure Storage credentials to upload images. These will be passed as environment variables to the Docker container via `docker-compose.yml`.

Change `AZURE_STORAGE_ACCOUNT_NAME` and `AZURE_STORAGE_ACCOUNT_KEY` in `docker-compose.yml`.

## 3. Building and Running the Entire Stack with Docker Compose

1. Ensure you are in the `week03/example-2` directory.

2. Build and start the services:

   ```bash
   docker compose up --build -d
   ```

3. Verify services are running (optional):

   ```bash
   docker compose ps
   ```

   You should see `product_db_container`, `order_db_container`, `product_api_container`, `order_api_container`, and `product_order_frontend` listed with Up status.

4. Access the applications:

   - Frontend Application: Open your web browser and go to `http://localhost:3000`
   - Product Service API (Swagger UI): Open your web browser and go to `http://localhost:8000/docs`
   - Order Service API (Swagger UI): Open your web browser and go to `http://localhost:8001/docs`

   You can now interact with the frontend to add products (including images), place orders, and view order details.

5. Persistent Storage in Action

   The `docker-compose.yml` explicitly defines named volumes: `product_db_data` and `order_db_data`.

   - These volumes are managed by Docker and store the actual PostgreSQL database files on your host machine in a location managed by Docker.

## 4. Stopping the Services

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
