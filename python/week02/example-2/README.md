# Week 02 Example 2: Full-Stack Microservice Deployment with Docker Compose

This example builds upon Week 02 Example 1 by introducing a frontend application and deploying the entire stack (Frontend, Product Microservice, and PostgreSQL Database) using Docker Compose. This demonstrates how to manage multi-service applications in a local development environment.

## 1. Project Setup

### 1.1. Clone the Repository

First, clone the repository to your local machine:

```bash
git clone https://github.com/durgeshsamariya/sit722_software_deployment_and_operation_code.git
```

- Navigate to the `example-2` directory: Ensure your terminal is in the root `example-2` directory, which contains `docker-compose.yml`, `backend/product_service/`, and `frontend/` folders.

  ```bash
  cd /week02/example-2
  ```

## 2. Docker Compose Deployment

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

## 3. Cleaning Up

To stop and remove all services and their associated Docker resources (containers), run:

```bash
docker compose down
```

This will stop the `db`, `product_service`, and `frontend` containers.
