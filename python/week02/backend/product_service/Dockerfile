# week02/backend/product_service/Dockerfile

# Use a specific, slim Python base image for a smaller final image size.
# python:3.10-slim provides necessary Python runtime without extra bulk.
FROM python:3.10-slim-buster

# Set the working directory inside the container.
# All subsequent commands (COPY, RUN, CMD) will be relative to this directory.
WORKDIR /app

# --- Dependency Installation ---
# Copy only the requirements file first. This allows Docker to cache this layer.
# If requirements.txt doesn't change, this layer (and pip install) won't be rebuilt.
COPY requirements.txt .


# Install Python dependencies.
# --no-cache-dir: Prevents pip from saving downloaded packages, reducing image size.
# --upgrade pip: Ensures pip itself is up-to-date.
# -r requirements.txt: Installs all packages listed in requirements.txt.
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# --- Application Code Copy ---
# Copy the application code after dependencies are installed.
# This leverages Docker's layer caching: if only code changes,
# the pip install layer (which is often slow) isn't invalidated.
COPY ./app /app

# --- Container Configuration ---
# Expose the port on which the FastAPI application will listen.
# This is mainly for documentation and network configuration awareness.
EXPOSE 8000

# Start the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
