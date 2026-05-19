# Hashing Microservice

A Python FastAPI microservice that provides image processing capabilities for the DAM system: perceptual hashing, cryptographic signing, and similarity/ownership verification.

## Prerequisites

- Python 3.11+
- pip
- virtualenv

## Setup

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Linux/macOS/WSL2:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment file and fill in your values
cp .env.example .env
```

## Running the Service

```bash
uvicorn main:app --reload --port 8001
```

The API will be available at `http://localhost:8001`. Interactive docs are at `http://localhost:8001/docs`.

## Running Tests

```bash
pytest tests/
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/hash` | Generate a perceptual hash for an uploaded image |
| `POST` | `/sign` | Sign an image hash with the configured Ethereum private key |
| `POST` | `/verify-ownership` | Verify that a signature matches a given hash and address |
| `POST` | `/verify-similarity` | Compare two images and return a similarity score |
