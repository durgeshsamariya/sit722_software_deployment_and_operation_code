# Product Service

# Product Service – Mini E-commerce Example

This is the Product microservice of a mini e-commerce app. It is built with **FastAPI** and uses **PostgreSQL** as the database.  
You will learn how to run a modern Python web service using Docker, and interact with it via REST endpoints.

---

## 1. Clone the Repository

```bash
git clone <REPO_URL>
cd <REPO_ROOT>/backend/product_service
```

---

## 2. Project Structure

product_service/
├── app/
│   ├── main.py        # FastAPI entry point
│   └── db.py          # Database config
├── requirements.txt   # Python dependencies
├── Dockerfile         # Build for FastAPI
└── docker-compose.yml # For local development

## 3. Run Locally (with Docker Compose)

You need Docker Desktop (or Docker Engine) installed.

1. Open a terminal and navigate to the product_service folder.

2. Run Docker Compose to build and start both the API and database:
`docker compose up --build`

3. Wait for both product_service and db containers to show as healthy.

4. The FastAPI service will be available at:
http://localhost:8000/docs
(This is the interactive API documentation provided by FastAPI.)

## 4. Example Endpoints

You can use the /docs page to try out the API, or tools like Postman or curl.

- List all products:
`GET /products/`
- Create a new product:
`POST /products/`
- Update stock quantity:
`PUT /products/{product_id}/stock`
- Get, update, delete by ID:
`GET /products/{id}, PUT /products/{id}, DELETE /products/{id}`

## 5. Stopping the Service

Press Ctrl+C in your terminal to stop the service,
then run:
`docker compose down`
to remove containers and networks.

