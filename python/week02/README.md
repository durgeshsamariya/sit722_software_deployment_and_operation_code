# Week 02: Product Microservice & Frontend Application

This project demonstrates a foundational mini e-commerce application focusing on a **Product Microservice** (built with Python FastAPI) and its accompanying **React Frontend**. It leverages Docker and Docker Compose for easy local development and deployment.

You will learn how to set up a multi-container application, manage database connections, interact with REST APIs, and ensure a clean, maintainable code structure.

---

## 1. Features

* **Product Management:**
    * Create new products with name, description, price, and stock quantity.
    * List all products with pagination and search capabilities.
    * Retrieve individual product details by ID.
    * Update existing product information (full or partial).
    * Update only the stock quantity of a product.
    * Delete products.
* **API Validation:** Robust input validation for all API endpoints.
* **Structured Code:** Separation of concerns for database models, API schemas, and main application logic.
* **Containerization:** All services are containerized using Docker.
* **Orchestration:** Docker Compose is used to define and run the multi-container application.
* **User Interface:** A simple, professional React frontend to interact with the Product Service API.

---

## 2. Technologies Used

**Backend (Product Service):**
* **Python 3.10+**
* **FastAPI:** High-performance web framework.
* **SQLAlchemy:** ORM (Object Relational Mapper) for database interaction.
* **PostgreSQL:** Relational database.
* **Uvicorn:** ASGI server.

**Frontend (React App):**
* **React 18+**
* **Vite:** Fast build tool for React.
* **React Router DOM:** For client-side routing.
* **Plain CSS:** For styling and professional design.

**Infrastructure:**
* **Docker:** Containerization platform.
* **Docker Compose:** Tool for defining and running multi-container Docker applications.

---

## 3. Project Structure

The project is organized into `backend` and `frontend` directories, each containing its respective service.

week02/
├── backend/
│   └── product_service/
│       ├── app/
│       │   ├── main.py        # FastAPI application entry point and API endpoints.
│       │   ├── db.py          # Database configuration, SQLAlchemy engine, and session management.
│       │   ├── models.py      # SQLAlchemy ORM models, defining the database table schema.
│       │   └── schemas.py     # Pydantic schemas for data validation and response serialization.
│       ├── tests/
│       │   └── test_main.py   # Pytest integration tests for the API.
│       ├── requirements.txt   # Production Python dependencies.
│       ├── requirements-dev.txt # Development and testing Python dependencies.
│       └── Dockerfile         # Dockerfile for the Product Service.
└── frontend/
    └── react-app/
    ├── public/
    ├── src/
    │   ├── App.jsx            # Main application layout and router setup.
    │   ├── main.jsx           # React entry point.
    │   ├── app.css            # Global styles and component-specific styles.
    │   ├── components/        # Reusable UI components (Button, InputField, ProductCard, ProductForm).
    │   └── pages/             # Top-level view components (ProductsPage, AddProductPage).
    ├── package.json
    ├── vite.config.js         # Vite configuration (if using Vite).
    └── Dockerfile             # Dockerfile for the React Frontend.
└── docker-compose.yml             # Orchestration file for both services.

---

## 4. Prerequisites

Before you begin, ensure you have the following installed on your local machine:

* **Git:** For cloning the repository.
* **Docker Desktop** (or Docker Engine): Essential for building and running containers.
* **PostgreSQL:** A local PostgreSQL server instance running (e.g., via Homebrew, apt, or a direct installer). The project connects to your host's PostgreSQL.
* **Python 3.10+ and pip:** For local development and running backend tests.
* **Node.js (LTS) and npm/yarn:** For local frontend development and building.

---

## 5. Setup Guide

Follow these steps to get the entire Week 02 project running on your local machine.

### 5.1. Clone the Repository

First, clone the repository to your local machine and navigate to the `week02` project root:

```bash
git clone <YOUR_REPO_URL>
cd <REPO_ROOT>/week02
```

### 5.2. Database Setup (Crucial!)

The backend Product Service connects to a local PostgreSQL database. You must manually create the products database before running the services. The application will create the necessary tables within this database on startup, but not the database itself.

1. Ensure your local PostgreSQL server is running.
2. Connect to your PostgreSQL server (e.g., using psql, pgAdmin, DBeaver, or your preferred SQL client).
    - If using psql (assuming default user postgres and password postgres):
    ```bash
    psql -h localhost -p 5432 -U postgres
    ```
    Enter postgres for the password when prompted.

3. Create the products database:
```sql
CREATE DATABASE products;
\q
```
(The product_service is configured to connect to a database named products by default.)

### 5.3. Build Docker Images

Navigate to the week02 root directory (where docker-compose.yml is located) and build the Docker images for both services:

```bash
docker compose build
```
This command will use the Dockerfile in each service's directory to create the necessary images.

## 6. Running the Application
Once the setup is complete, you can start the entire application stack using Docker Compose.

1. Ensure your local PostgreSQL server is running.

2. Navigate to the week02 root directory in your terminal:

```bash
cd <REPO_ROOT>/week02
```

3. Start the services:
```bash
docker compose up -d
```

- -d: Runs the containers in detached mode (in the background).
- To see logs: docker compose logs -f (follow logs).

4. Verify Service Health:
You can check the status of your running containers:

```bash
docker compose ps
```

Ensure both product_service_container and react_app_container are Up. 

### 6.1 6.1. Accessing the Application

Once the containers are running:

- Frontend Application: Open your web browser and go to:
    http://localhost:3000
    You should see the Product Catalog UI.

- Backend Product Service API Documentation (Swagger UI):
    Open your web browser and go to:
    http://localhost:8000/docs
    This provides an interactive documentation where you can test the API endpoints directly.

