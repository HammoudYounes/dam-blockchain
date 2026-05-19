# Backend API

A NestJS REST API that acts as the gateway between the frontend, the hashing microservice, and the Polygon blockchain.

## Prerequisites

- Node.js 20
- npm
- Docker (for containerised runs)

## Setup

```bash
npm install

# Copy environment file and fill in your values
cp .env.example .env
```

## Running in Development

```bash
npm run start:dev
```

The server starts at `http://localhost:3001`. Swagger documentation is available at `http://localhost:3001/api/docs`.

## Running Tests

```bash
npm run test
```

## Running with Docker

```bash
docker compose up
```

## Modules

| Module | Responsibility |
|--------|---------------|
| `ImageModule` | Receives image uploads, calls the hashing service, stores metadata |
| `SignatureModule` | Manages cryptographic signatures for assets |
| `NftModule` | Handles minting and querying NFTs on the Polygon network |
| `AuthModule` | Wallet-based authentication and JWT issuance |
