FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Copy code
COPY ./app /app/app
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy your tests so pytest can discover them
COPY tests/ ./tests

# Run FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
