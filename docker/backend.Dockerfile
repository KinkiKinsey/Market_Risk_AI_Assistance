# Backend Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY config.env* ./ 2>/dev/null || true

# Set Python path
ENV PYTHONPATH=/app/backend:/app:$PYTHONPATH

# Expose port
EXPOSE 8000

# Run API server
WORKDIR /app/backend
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]

