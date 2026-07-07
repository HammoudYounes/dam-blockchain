# --- Stage 1: Build ---
FROM python:3.12-slim AS builder

WORKDIR /work

# Install system dependencies needed for compiling some python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies into a local folder
COPY ./requirements-deploy.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements-deploy.txt --extra-index-url https://download.pytorch.org/whl/cpu

# --- Stage 2: Runtime ---
FROM python:3.12-slim

WORKDIR /work

# Copy only the installed python packages from the builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY . /work/app

# Set environment variables for better performance and smaller cache footprints
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/work/app

# Expose port and start
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
