FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Copy code
COPY ./app ./app
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
