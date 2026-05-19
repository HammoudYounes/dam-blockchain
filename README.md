# Blockchain-backed Digital Asset Management (DAM) System

A monorepo implementing a blockchain-backed Digital Asset Management system that uses perceptual hashing, cryptographic signatures, and NFTs on the Polygon network to prove asset ownership and detect unauthorized copies.

## Monorepo Structure

| Layer | Directory | Stack | Purpose |
|-------|-----------|-------|---------|
| Hashing | `/hashing` | Python 3.11, FastAPI | Image processing microservice: perceptual hashing, signing, ownership and similarity verification |
| Smart Contracts | `/contracts` | Solidity, Hardhat, Ethers.js | EVM smart contracts for asset registration, signatures, and ownership verification on Polygon |
| Backend API | `/backend` | NestJS, TypeScript | REST API gateway that orchestrates the hashing service and blockchain interactions |
| Frontend | `/frontend` | Next.js 14, TypeScript | Web application for wallet connection, asset upload, minting, and verification |

## Prerequisites

- **WSL2** — required on Windows for running the Python service and Docker
- **Node.js 20** — for the contracts, backend, and frontend layers
- **Python 3.11+** — for the hashing microservice
- **Docker** — for running the backend with `docker compose up`
- **MetaMask** — browser extension for wallet connection in the frontend

## Branch Convention

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases, tagged per phase (e.g. `v1.0.0-phase1`) |
| `develop` | Integration branch; merge feature branches here first |
| `feature/<name>` | Feature work branched from `develop` |

All pull requests target `develop`. Merges to `main` are made at phase milestones and tagged.

## Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use for |
|--------|---------|
| `feat` | New features |
| `fix` | Bug fixes |
| `test` | Adding or updating tests |
| `docs` | Documentation changes only |
| `chore` | Tooling, configuration, dependencies |

Example: `feat(hashing): add perceptual hash endpoint`

## Getting Started

Refer to the `README.md` in each sub-directory for layer-specific setup instructions:

- [Hashing service](./hashing/README.md)
- [Smart contracts](./contracts/README.md)
- [Backend API](./backend/README.md)
- [Frontend](./frontend/README.md)
