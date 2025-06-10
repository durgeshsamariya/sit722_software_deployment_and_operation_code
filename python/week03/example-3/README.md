# Week 03 - Example 3: E-commerce Microservices with Asynchronous Communication

This example demonstrates a more advanced microservices architecture for an e-commerce application, building upon previous examples. It introduces a new dedicated Customer Microservice and implements asynchronous, event-driven communication between the Order and Product services using RabbitMQ.

---

## 🚀 Architecture Overview

This project consists of five main components orchestrated using Docker Compose:

1.  **Product Microservice (FastAPI/Python)**:
    * Manages product data (name, description, price, stock).
    * Handles image uploads to Azure Blob Storage.
    * **New**: Consumes `order.placed` events from RabbitMQ to asynchronously deduct product stock.
    * **New**: Publishes `product.stock.deducted` or `product.stock.deduction.failed` events back to RabbitMQ.
    * Uses a dedicated PostgreSQL database (`product_db`).
2.  **Order Microservice (FastAPI/Python)**:
    * Manages customer orders and their items.
    * **New**: Synchronously validates `customer_id` with the Customer Microservice during order creation.
    * **New**: Publishes `order.placed` events to RabbitMQ after an order is initially saved with a `pending` status.
    * **New**: Consumes `product.stock.deducted` or `product.stock.deduction.failed` events from RabbitMQ to update the order status to `confirmed` or `failed` respectively.
    * Uses a dedicated PostgreSQL database (`order_db`).
3.  **Customer Microservice (FastAPI/Python)**:
    * **New Service**: Manages all customer profiles and data (email, name, address, basic password storage).
    * Provides CRUD (Create, Read, Update, Delete) endpoints for customer management.
    * Uses a dedicated PostgreSQL database (`customer_db`).
4.  **RabbitMQ Message Broker**:
    * **New Component**: Facilitates asynchronous communication between services.
    * Decouples the Order and Product services, making the order placement flow more resilient and responsive.
5.  **Frontend (Nginx/HTML/CSS/JavaScript)**:
    * A simple web interface for interacting with all three backend microservices.
    * Allows adding/viewing products, adding/viewing customers, managing a shopping cart, and placing orders.
    * **New**: Reflects asynchronous order status updates (`pending`, `confirmed`, `failed`).

---

## ✨ Key Features

* **Microservices Architecture**: Clearly separated Product, Order, and Customer domains.
* **Asynchronous Communication**: Implements event-driven patterns using **RabbitMQ** for reliable stock deduction.
* **Customer Management**: Dedicated service for handling customer profiles.
* **Distributed Transactions (Basic Saga)**: Order status updates (`pending` -> `confirmed`/`failed`) are driven by events from the Product Service, demonstrating eventual consistency.
* **Persistent Data**: Each microservice uses its own PostgreSQL database with Docker volumes for data persistence.
* **Image Uploads**: Product images are stored securely in Azure Blob Storage.
* **Comprehensive CRUD**: Full Create, Read, Update, Delete functionality for Products, Orders, and Customers.
* **Responsive Frontend**: Simple web UI to interact with all services.

---

## ⚙️ Prerequisites

Before you begin, ensure you have the following installed:

* **Docker Desktop**: Includes Docker Engine and Docker Compose.
    * [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
* **Azure Storage Account**: Required for product image uploads.
    * You'll need your **Storage Account Name** and **Storage Account Key**.
    * Create a **Blob Container** within your storage account; `product-images-e3` is recommended, but you can use any name and configure it in `.env`.

---

## 🚀 Getting Started

Follow these steps to set up and run the entire application stack using Docker Compose.

### 1. Clone the Repository (if you haven't already)

Navigate to your project root where the `week03` folder is located:

```bash
git clone <your-repository-url>
cd <your-repository-name>/week03/example-3
```

### 2. Build and Start the Services

Navigate to the week03/example-3 directory in your terminal:
```bash
cd your_project_folder/week03/example-3
```

Now, run the Docker Compose command to build the images and start all containers:

```bash
docker compose up --build -d
```

- `--build`: Ensures Docker images are rebuilt, picking up the latest code changes.
- `-d`: Runs the containers in detached mode (in the background).
This process might take a few minutes as Docker downloads images and builds your services.

### 4. Verify Services are Running

You can check the status of all running containers:

```bash
docker compose ps
```

You should see all eight services (`rabbitmq`, `product_db`, `order_db`, `customer_db`, `product_service`, `order_service`, `customer_service`, `frontend`) listed with a Up status.

## 🌐 Accessing the Application
Once all services are up:

- Frontend Application: http://localhost:3000

- Product Service API (Swagger UI): http://localhost:8000/docs

- Order Service API (Swagger UI): http://localhost:8001/docs

- Customer Service API (Swagger UI): http://localhost:8002/docs

- RabbitMQ Management UI: http://localhost:15672 (Login with guest/guest) You can observe message queues and exchanges here.


## 🧹 Cleanup
To stop and remove all Docker containers, networks, and volumes created by Docker Compose (this will delete your database data, ensuring a clean slate for the next run):

```bash
docker compose down --volumes
```

This is useful for a completely fresh start or when you're done with the example.