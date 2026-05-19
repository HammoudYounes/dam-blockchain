# Frontend

A Next.js 14 web application for interacting with the DAM system: connect a wallet, upload and mint digital assets, and verify ownership or similarity.

## Prerequisites

- Node.js 20
- MetaMask browser extension (for wallet connection)

## Setup

```bash
npm install

# Copy environment file and fill in your values
cp .env.example .env.local
```

## Running in Development

```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

## Building for Production

```bash
npm run build
```

## Pages

| Route | Description |
|-------|-------------|
| `/auth` | Wallet connection — sign in with MetaMask |
| `/dashboard` | Asset grid — browse and manage your registered assets |
| `/upload` | Mint flow — upload an image, hash it, sign it, and mint the NFT |
| `/verify` | Signature verification — verify ownership or check image similarity |
