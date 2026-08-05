# Backend Phase — Task List

Greenfield NestJS build. The backend is the REST gateway between the frontend, the
hashing microservice (`/hashing`), and the deployed Polygon Amoy contracts (`/contracts`).

Tasks are sized to ~one PR / a few hours each. IDs let you track dependencies.

---

## Base-code findings (as of 2026-07-22)

| Layer | State | Impact on backend |
|---|---|---|
| `/backend` | Empty NestJS scaffold — only `.env.example`, `README.md`, 4 empty module dirs (`auth`, `image`, `nft`, `signature`) with `.gitkeep`. **No `package.json`, `main.ts`, `app.module.ts`, `tsconfig`, `nest-cli.json`, Dockerfile.** | Nothing is initialized — build from zero. |
| `/contracts` | ✅ Deployed & verified on **Polygon Amoy** (chainId 80002). ABIs via `hardhat compile`. | Backend calls these; interfaces confirmed below. |
| `/hashing` | FastAPI contract documented (`/hash`, `/sign`, `/verify-ownership`, `/verify-similarity`), but **no `main.py` app entrypoint exists yet**. | Backend integrates over HTTP; app is the hashing team's deliverable. |
| `/frontend` | Empty scaffold. | Consumes backend at `:3001`. |

### Confirmed contract interfaces
- **DAMAsset**: `mintAsset(creator,uri)→tokenId`, `transferAsset(tokenId,to)`, `creatorOf(tokenId)`, `isURIRegistered(uri)`; events `AssetMinted`, `AssetTransferred`
- **DAMSignature**: `registerSignature(tokenId,pHash,r,s,v,creator)`, `getAssetSignature(tokenId)`, `isRegistered(tokenId)`, `isHashRegistered(pHash)`; event `AssetRegistered`
- **DAMVerifier**: `verifySignature(tokenId,hash)` (tx), `verifySignatureView(tokenId,hash)` (free view); event `VerificationPerformed`

### Issues to fix early
1. `backend/.env.example` references **Mumbai** (`POLYGON_MUMBAI_RPC_URL`) but contracts are on **Amoy** (Mumbai is deprecated). Var names also don't match `contracts/.env` (`ALCHEMY_AMOY_URL`, `DAM_ASSET_ADDRESS`, …). → **B0.4**
2. ~~**No `DATABASE_URL`** anywhere → open decision: on-chain + IPFS only, or add a DB?~~
   → **Resolved in [DESIGN.md](./DESIGN.md): Postgres + Prisma**, as a projection of chain
   state plus saga/operational state. Chain stays authoritative for ownership and proof.

---

## Epic D — Design *(precedes implementation; produces artefacts, not code)*
- [x] **BD.1** Data-model design: access patterns → chain gap analysis → schema. → [DESIGN.md](./DESIGN.md)
- [x] **BD.2** Persistence decision record (B8.0) with rejected alternatives. → [DESIGN.md §3](./DESIGN.md)
- [x] **BD.3** Mint saga state machine + compensation/resume semantics. → [DESIGN.md §7](./DESIGN.md)
- [ ] **BD.4** API contract design: endpoint list, request/response shapes, error taxonomy, status codes. Agree with frontend **before** B0.6 writes Swagger.
- [ ] **BD.5** Auth flow design: nonce lifecycle, SIWE message format, token TTL/refresh, which routes are guarded. Blocked on open question §10.1 (who signs — user or service key?).
- [ ] **BD.6** Sequence diagrams for the three critical flows (mint, verify-ownership, verify-similarity) spanning frontend → backend → hashing → chain.
- [ ] **BD.7** Failure-mode design: what the user sees for each of `Orphaned`, hashing-service-down, RPC timeout, insufficient gas.

## Epic 0 — Project Bootstrap
- [ ] **B0.1** Initialize NestJS app: `package.json`, `tsconfig.json`, `nest-cli.json`, `src/main.ts`, `src/app.module.ts`. Server boots on `PORT=3001`.
- [ ] **B0.2** Add ESLint + Prettier config, `.gitignore` for `dist/` `node_modules/`.
- [ ] **B0.3** `ConfigModule` (global) + env schema validation (Joi/zod) covering every var in `.env.example`.
- [ ] **B0.4** Clean up `.env.example`: Mumbai→Amoy, align var names with contracts (`ALCHEMY_AMOY_URL`, `DAM_ASSET_ADDRESS`, …), add chainId `80002`.
- [ ] **B0.5** Global `ValidationPipe`, global exception filter, unified response/error shape, CORS for frontend origin.
- [ ] **B0.6** Swagger/OpenAPI at `/api/docs` (README already advertises it).
- [ ] **B0.7** Structured logging (Nest Logger or pino) + request logging interceptor.
- [ ] **B0.8** `GET /health` endpoint (liveness + downstream reachability check).

## Epic 1 — Blockchain Integration Layer (`BlockchainModule`, shared)
- [ ] **B1.1** Vendor the 3 contract ABIs into `src/blockchain/abis/` (copy `abi` field from `contracts/artifacts/...`).
- [ ] **B1.2** Provider + signer factory (ethers v6): `JsonRpcProvider` from RPC URL, `Wallet` from `DEPLOYER_PRIVATE_KEY`.
- [ ] **B1.3** Contract instance providers for DAMAsset / DAMSignature / DAMVerifier (injectable).
- [ ] **B1.4** Utility: `boolArrayToBytes32(bool[64])` + `signatureToRSV(rawSig)` (per contracts README), with unit tests.
- [ ] **B1.5** Tx helper: send → `wait()` → parse event args (e.g. extract `tokenId` from `AssetMinted`); typed errors for reverts/gas.

## Epic 2 — Hashing Service Client (`HashingModule`)
- [ ] **B2.1** `HttpModule`/axios client keyed off `HASHING_SERVICE_URL` with timeout + retry.
- [ ] **B2.2** Typed request/response DTOs for `/hash`, `/sign`, `/verify-ownership`, `/verify-similarity`.
- [ ] **B2.3** `HashingService` wrapper methods for the 4 endpoints + error mapping (service down → 502).

## Epic 3 — IPFS / Pinata (`IpfsModule`)
- [ ] **B3.1** Pinata client service using `PINATA_API_KEY`/`PINATA_SECRET_KEY`: `pinFile()` + `pinJSON()`.
- [ ] **B3.2** ERC-721 metadata builder (name, description, image `ipfs://…`, attributes) → returns metadata URI.

## Epic 4 — Auth (`AuthModule`)
- [ ] **B4.1** `GET /auth/nonce?address=` — issue + cache a per-wallet nonce.
- [ ] **B4.2** `POST /auth/login` — verify wallet signature of nonce (SIWE-style), recover address.
- [ ] **B4.3** JWT issuance (`JWT_SECRET`) + `JwtStrategy` + `JwtAuthGuard`.
- [ ] **B4.4** `GET /auth/me` and apply guard to protected routes.

## Epic 5 — Image (`ImageModule`)
- [ ] **B5.1** `POST /images/upload` — multipart upload (multer), validate MIME type + size limit.
- [ ] **B5.2** Orchestration: uploaded file → `HashingService.hash()` → return pHash (+ temp store).
- [ ] **B5.3** Duplicate pre-check via `isHashRegistered`/`isURIRegistered` before minting.
- [ ] **B5.4** Image DTOs + Swagger annotations.

## Epic 6 — NFT (`NftModule`)
- [ ] **B6.1** Mint flow: pin image→IPFS → build metadata→IPFS → `mintAsset()` → parse `tokenId`.
- [ ] **B6.2** Signature registration: `HashingService.sign(pHash)` → split r/s/v → `registerSignature()`.
- [ ] **B6.3** Combined `POST /nft/mint` endpoint chaining B6.1 + B6.2 (transactional/rollback semantics).
- [ ] **B6.4** Read endpoints: `GET /nft/:tokenId` (tokenURI + `creatorOf` + `ownerOf` + `isRegistered`).
- [ ] **B6.5** `POST /nft/:tokenId/transfer` → `transferAsset()`.
- [ ] **B6.6** NFT DTOs + Swagger.

## Epic 7 — Signature / Verification (`SignatureModule`)
- [ ] **B7.1** `POST /verify/ownership` — image → hash → `verifySignatureView(tokenId, hash)` (free).
- [ ] **B7.2** `POST /verify/similarity` — proxy to hashing `/verify-similarity`, return score + verdict.
- [ ] **B7.3** `GET /signature/:tokenId` → `getAssetSignature()` (decoded, human-readable).

## Epic 8 — Persistence *(decided — see [DESIGN.md](./DESIGN.md))*
- [x] **B8.0** ✅ **Decided**: Postgres + Prisma. DB is a projection + operational state; chain stays authoritative.
- [ ] **B8.1** `PrismaModule` + `schema.prisma` for `users`, `assets`, `asset_fingerprints`, `asset_signatures`, `mint_jobs`, `verifications`, `chain_sync_cursor`; initial migration.
- [ ] **B8.2** Repository layer + `/dashboard` queries: assets by `creator_address` / `owner_address`, paginated, returning `indexedAtBlock`.
- [ ] **B8.3** `mint_jobs` saga persistence + resume worker (recovers `Orphaned` jobs on boot); `idempotency_key` on `POST /nft/mint`. **Reshapes B6.3.**
- [ ] **B8.4** Chain indexer: poll `AssetMinted`/`AssetTransferred`/`AssetRegistered` from `chain_sync_cursor`, idempotent on `(tx_hash, log_index)`, ~30-block reorg lag.
- [ ] **B8.5** Similarity candidate search over `phash64` (Hamming/`bit_count`), feeding the combiner model in B7.2.

## Epic 9 — Testing
- [ ] **B9.1** Unit tests for `BlockchainModule` utils + services (mock ethers).
- [ ] **B9.2** Unit tests for `HashingService` + `IpfsService` (mock HTTP).
- [ ] **B9.3** E2E tests for auth, mint, verify flows (mocked chain + hashing).

## Epic 10 — DevOps
- [ ] **B10.1** `Dockerfile` (multi-stage, Node 20).
- [ ] **B10.2** `docker-compose.yml` wiring backend + hashing service (+ DB if B8).
- [ ] **B10.3** CI workflow (lint + test + build) in `.github/`.
- [ ] **B10.4** Update `backend/README.md` with real endpoints once built.

---

## Suggested order

```
Epic D → Epic 0 → Epic 1 → Epic 2 / Epic 3 (parallel) → Epic 8.1 → Epic 4
      → Epic 5 / 6 / 7 (+ 8.2–8.5) → Epic 9 → Epic 10
```

Epic D is not a formality — **BD.4** (API contract) blocks the frontend from starting, and
**BD.5** is blocked on [DESIGN.md §10.1](./DESIGN.md): whether the *creator* or the *service
key* signs the hash. That answer changes the mint saga's shape, so settle it before Epic 6.

Schema (**B8.1**) now lands before Epic 5, since Image/NFT modules write to it.
