# Smart Contracts

Solidity smart contracts for the DAM system, compiled and deployed with Hardhat. Targets the Polygon Mumbai testnet.

## Prerequisites

- Node.js 20
- npm

## Setup

```bash
npm install

# Copy environment file and fill in your values
cp .env.example .env
```

## Compile

```bash
npx hardhat compile
```

## Test

```bash
npx hardhat test
```

## Coverage

```bash
npx hardhat coverage
```

## Local Development Node

```bash
npx hardhat node
```

This starts a local JSON-RPC node at `http://localhost:8545` with pre-funded test accounts.

## Deploy to Polygon Mumbai

```bash
npx hardhat ignition deploy
```

Ensure your `.env` is populated with a funded wallet private key and valid Alchemy and Polygonscan API keys before deploying.
