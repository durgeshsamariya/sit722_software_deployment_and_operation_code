# week03/example-2/backend/order_service/Dockerfile

# Use the official Python image as a base for our FastAPI application
FROM python:3.10-slim-buster

# Set the working directory inside the container
WORKDIR /code

# Copy only the requirements file first to leverage Docker cache
# If requirements.txt doesn't change, this layer is cached, speeding up builds
COPY requirements.txt .

# Install Python dependencies
# Use --no-cache-dir to prevent caching package data, reducing image size
# Use --upgrade pip to ensure pip is up-to-date
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application code into the container
# This copies the 'app' directory (main.py, db.py, models.py, schemas.py)
COPY app /code/app

# Expose the port that the FastAPI application will run on
EXPOSE 8001

# Command to run the application using Uvicorn
# --host 0.0.0.0 makes the server accessible from outside the container
# --port 8001 specifies the port
# The DB_HOST environment variable will be set via Docker Compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]