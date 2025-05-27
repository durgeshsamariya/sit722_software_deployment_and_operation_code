# week02/backend/product_service/Dockerfile

FROM python:3.10-slim

WORKDIR /app

# Copy only the app code and requirements.txt
COPY ./app /app
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose FastAPI port for clarity
EXPOSE 8000

# Start the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
