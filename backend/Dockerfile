# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Prevent Python from writing bytecode files and enable unbuffered console output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install runtime system packages (curl for container health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code (excluding files defined in .dockerignore)
COPY app/ ./app/
COPY scripts/ ./scripts/

# Expose FastAPI service port
EXPOSE 8000

# Run Uvicorn ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
