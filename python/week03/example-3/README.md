# Week 03 - Example 3: E-commerce Microservices with Asynchronous Communication

This example demonstrates a more advanced microservices architecture for an e-commerce application, building upon previous examples. It introduces a new dedicated Customer Microservice and implements asynchronous, event-driven communication between the Order and Product services using RabbitMQ.

## Prerequisites

- **Azure Storage Account**: Required for product image uploads.
  - You'll need your **Storage Account Name** and **Storage Account Key**.
  - Create a **Blob Container** within your storage account; `product-images` is recommended.

## Getting Started

Follow these steps to set up and run the entire application stack using Docker Compose.

### 1. Navigate to `example-03` directory:

Navigate to the `week03/example-3` directory in your terminal:

```bash
cd your_project_folder/week03/example-3
```

### 2. Build and Start the Services

Now, run the Docker Compose command to build the images and start all containers:

```bash
docker compose up --build -d
```

- `--build`: Ensures Docker images are rebuilt, picking up the latest code changes.
- `-d`: Runs the containers in detached mode (in the background).
  This process might take a few minutes as Docker downloads images and builds your services.

### 3. Verify Services are Running

You can check the status of all running containers:

```bash
docker compose ps
```

You should see all eight services (`rabbitmq`, `product_db`, `order_db`, `customer_db`, `product_service`, `order_service`, `customer_service`, `frontend`) listed with a Up status.

## Accessing the Application

Once all services are up:

- Frontend Application: http://localhost:3000

- Product Service API (Swagger UI): http://localhost:8000/docs

- Order Service API (Swagger UI): http://localhost:8001/docs

- Customer Service API (Swagger UI): http://localhost:8002/docs

- RabbitMQ Management UI: http://localhost:15672 (Login with guest/guest) You can observe message queues and exchanges here.

## Cleanup

To stop and remove all Docker containers, networks, and volumes created by Docker Compose (this will delete your database data, ensuring a clean slate for the next run):

```bash
docker compose down --volumes
```

This is useful for a completely fresh start or when you're done with the example.
