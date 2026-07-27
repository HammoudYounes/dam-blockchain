# Backend Phase — Task List

**Revised:** 2026-07-24 · **Supersedes:** the 2026-07-22 list · **Source:** [DESIGN.md](./DESIGN.md)

Greenfield NestJS build. The backend is **T2** in the five-tier architecture — the REST
gateway between the client (T1), the hashing service (T3), IPFS (T4), and the three deployed
Polygon Amoy contracts (T5).

Tasks are sized to ~one PR each. IDs are stable: [PLAN.md](./PLAN.md) references them, so
revised tasks keep their number rather than being renumbered.

Legend: ⟳ revised · ✚ new · ✗ removed — all relative to the 2026-07-22 list.

---

## What changed and why

Seven tasks in the previous list described work that cannot be built as written. Each
correction below is traceable to contract code or shipped source, not opinion.

| Task | Was | Now | Evidence |
|---|---|---|---|
| **BD.5** | blocked on "who signs?" | **unblocked** — the creator signs at T1 | `verifySignatureView` recovers and compares to `creator`; T3 has no signing capability at all |
| **B2.x** | client for `/hash`, `/sign`, `/verify-ownership`, `/verify-similarity` | client for `/hash`, `/similarity`, `/index` | shipped T3 exposes none of the old four; `/sign` and `/verify-ownership` should not exist |
| **B6.2** | `HashingService.sign(pHash)` | verify a client signature, then submit it | T3 has no `eth_account`/`web3`; the signature must recover to `creator` |
| **B6.5** | backend calls `transferAsset()` | client calls it directly; backend only reconciles | `require(ownerOf(tokenId) == msg.sender)` — the service wallet is never the owner |
| **B8.4** | index `AssetMinted`/`AssetTransferred`/`AssetRegistered` | index the **standard ERC-721 `Transfer`** | `transferAsset` is an optional wrapper; standard transfers never emit `AssetTransferred` |
| **B8.5** | Postgres popcount candidate search | ✗ removed — belongs to T3 | the similarity index lives in T3, keyed on backend-supplied `assetId` |
| **B5.3** | pre-check "via `isHashRegistered`/`isURIRegistered`" | `isHashRegistered` only, before signing | the URI does not exist until after pinning, so it cannot be pre-checked |

---

## Base-code findings (as of 2026-07-24)

| Layer | State | Impact on T2 |
|---|---|---|
| `/backend` | Empty scaffold — 4 empty module dirs, a stale `.env.example`, a README advertising endpoints that do not exist. **No `package.json`.** `prisma/schema.prisma` + `sql/init.sql` + `schema.dbml` are written but **never migrated**. | Build from zero. Nothing can run until B0.1. |
| `/contracts` | ✅ Deployed + verified on Amoy (80002). 35/35 tests pass. ABIs available after `npx hardhat compile`. | Interfaces confirmed below — **read the security caveats before designing against them**. |
| `/hashing` | ✅ `main.py` **exists and runs**. But it exposes `POST /similarity`, `POST|GET|DELETE /image`, `GET /` — **none of the four endpoints its README documents**. No `/hash`, no `/sign`. No `eth_account`/`web3` anywhere. | The T3 contract must be renegotiated. See **BD.8**. |
| `/frontend` | Empty scaffold. No `package.json`. | Consumes T2 at `:3001`. Must implement signing (Flow 2) and direct transfer (Flow 4). |
| infra | `compose.yaml` has only `hashing-service`. **No Postgres, no backend.** CI covers hashing only. | See **B0.9**. |

### Blocking external gaps

1. **T3 cannot boot from a clean clone.** `api/similarity.py` calls `joblib.load()` at import
   time on `data/model/copymint_logreg.joblib`, which is neither committed (blocked by
   `hashing/data/*` in `.gitignore`) nor present on disk. FAISS index files are gitignored too.
2. **T3 has no `/hash` endpoint**, so nothing produces a standalone pHash today. `get_hash()`
   already exists in `utils/hash_utils.py` — exposing it is small, but it is not our code.

### Confirmed contract interfaces

- **DAMAsset**: `mintAsset(creator,uri)→tokenId` · `transferAsset(tokenId,to)` ·
  `creatorOf(tokenId)` · `isURIRegistered(uri)` · plus the full **standard ERC-721 surface**
  (`transferFrom`, `safeTransferFrom`, `ownerOf`, `tokenURI`, `approve`)
  Events: `AssetMinted`, `AssetTransferred`, **`Transfer`** ← index this one
- **DAMSignature**: `registerSignature(tokenId,pHash,r,s,v,creator)` · `getAssetSignature(tokenId)`
  · `isRegistered(tokenId)` · `isHashRegistered(pHash)` — event `AssetRegistered`
- **DAMVerifier**: `verifySignature(tokenId,hash)` (tx, ~41k gas) · `verifySignatureView(tokenId,hash)`
  (free view, **can revert**) — event `VerificationPerformed`

### Contract security caveats — design around these

Confirmed by executable proof-of-concept. Full write-up in [DESIGN.md §8](./DESIGN.md).

| # | Issue | Severity | Our exposure |
|---|---|---|---|
| 1 | `registerSignature` accepts **unminted** token ids and never verifies the signature — a predictable `_nextTokenId` lets anyone permanently lock future tokens | 🔴 HIGH | New terminal saga state (**B6.7**); escalate (**BD.9**) |
| 2 | `AssetTransferred` is bypassed by every standard transfer | 🔴 HIGH | Fixed entirely on our side (**B8.4**) |
| 3 | `DAMSignature` and `DAMAsset` can disagree about `creator` | 🟡 MED | Render only `verifySignatureView` as authorship (**B6.4**, **B7.1**) |
| 4 | `verifySignatureView` reverts rather than returning `false` | 🟡 MED | Revert taxonomy (**B7.1**) |

---

## Epic D — Design *(produces artefacts, not code)*

- [x] **BD.1** Data-model design → [DESIGN.md](./DESIGN.md)
- [x] **BD.2** Persistence decision record (B8.0) → [DESIGN.md §7](./DESIGN.md)
- [x] **BD.3** Mint saga state machine → [DESIGN.md §4.3](./DESIGN.md)
- [x] ⟳ **BD.5** ~~Blocked on §10.1~~ → **RESOLVED: the creator signs at T1.** Nonce lifecycle,
      SIWE format, JWT TTL, guarded routes → [DESIGN.md §3](./DESIGN.md)
- [ ] **BD.4** **API contract** — endpoint list, request/response shapes, error taxonomy,
      status codes for `/auth/*`, `/images/*`, `/nft/*`, `/verify/*`, `/dashboard`.
      **Blocks B0.6, B5.4, B6.6 and the entire frontend.** Timebox to half a day; publish a
      draft rather than blocking on consensus.
- [ ] ✚ **BD.8** **T3 service contract** — agree the four endpoints below with the hashing
      team. **Blocks Epic 2, B5.2, B7.2.**
      - `POST /hash` → all 6 hashes with `bits`, `bit_length`, `algo_version`, plus
        `phash_bytes32` packed for the chain
      - `POST /similarity` → candidates keyed on the **`assetId` T2 supplied**, never a filename
      - `POST /index` `{assetId, image}` · `DELETE /index/{assetId}`
      - `/sign` and `/verify-ownership` are **dropped**, with the reasons from BD.5
      - Also required: commit the logreg model + index files, or provide a build step
- [ ] ✚ **BD.9** **Escalate the two HIGH contract findings** to the Epic 1 owner. Decide:
      redeploy with fixes in a later phase, or accept the risk for the demo. Record the answer.
- [ ] **BD.6** Sequence diagrams for the five flows → largely covered by
      [DESIGN.md §3–5](./DESIGN.md); extend to the frontend's own steps
- [ ] **BD.7** Failure-mode design: what the user sees for `orphaned`, `unregisterable`,
      T3 down, RPC timeout, insufficient gas

## Epic 0 — Bootstrap

- [ ] **B0.1** Initialize NestJS: `package.json`, `tsconfig.json`, `nest-cli.json`,
      `src/main.ts`, `src/app.module.ts`. Boots on `PORT=3001`. **Blocks everything.**
- [ ] **B0.2** ESLint + Prettier, `.gitignore` for `dist/`, `node_modules/`
- [ ] **B0.3** Global `ConfigModule` + zod env validation. Fail loudly at **boot**, not at
      first use
- [ ] ⟳ **B0.4** Rewrite `.env.example`: `POLYGON_MUMBAI_RPC_URL`→`ALCHEMY_AMOY_URL`,
      `DAM_*_CONTRACT_ADDRESS`→`DAM_*_ADDRESS`, add `CHAIN_ID=80002`, `DATABASE_URL`,
      `MAX_UPLOAD_SIZE`
- [ ] **B0.5** Global `ValidationPipe` (whitelist, transform), exception filter, unified error
      shape from BD.4, CORS for the frontend origin
- [ ] **B0.6** Swagger at `/api/docs` — module only; per-endpoint annotations ship with their
      modules. *Blocked on BD.4.*
- [ ] **B0.7** pino + request-id interceptor. **Redact** `authorization`, `JWT_SECRET`,
      `PINATA_SECRET_KEY`, `DEPLOYER_PRIVATE_KEY` — set up before there is anything to leak
- [ ] **B0.8** `GET /health` — liveness + Postgres `SELECT 1` + T3 reachability. Report a
      degraded downstream in the body; **do not 503 the whole app**
- [ ] ✚ **B0.9** **Add Postgres to `compose.yaml`** (image, volume, healthcheck, `DATABASE_URL`).
      **Blocks B8.1** — the schema cannot be migrated without a database
- [ ] ✚ **B0.10** Rate limiting (`@nestjs/throttler`) on the public routes. `/verify/similarity`
      runs FAISS + six hash algorithms and is the most CPU-expensive call in the system;
      `/nft/mint` spends real gas per call

## Epic 1 — Blockchain layer (`BlockchainModule`, shared) — *not my slice*

- [ ] **B1.1** Vendor the 3 ABIs into `src/blockchain/abis/`
- [ ] **B1.2** Provider + signer factory (ethers v6): `JsonRpcProvider`, `Wallet` from
      `DEPLOYER_PRIVATE_KEY`
- [ ] **B1.3** Injectable contract instances for DAMAsset / DAMSignature / DAMVerifier
- [ ] ⟳ **B1.4** `boolArrayToBytes32(bool[64])` + `signatureToRSV(rawSig)`, **plus
      `verifyPHashSignature()`** wrapping `ethers.verifyMessage` on the raw 32 bytes.
      Unit-test the 32-vs-66-byte prefix trap explicitly — signing the hex string instead of
      the bytes produces a permanently unverifiable signature
- [ ] **B1.5** Tx helper: send → `wait()` → parse event args; typed errors for reverts/gas
- [ ] ✚ **B1.6** **Read-only provider** with no signer, for the free view calls
      (`isHashRegistered`, `verifySignatureView`, `ownerOf`). These need no key and no gas;
      keeping them off the signing path removes a whole class of accident

## Epic 2 — Hashing client (`HashingModule`) — ⟳ rewritten

*Blocked on BD.8. Build to the agreed contract against mocks; the mocks are the spec.*

- [ ] ⟳ **B2.1** Axios client on `HASHING_SERVICE_URL` with timeout + retry. **Retry only
      idempotent calls** — `/index` is not one
- [ ] ⟳ **B2.2** Typed DTOs for `/hash`, `/similarity`, `/index`, `DELETE /index/{assetId}`
      *(was: `/hash`, `/sign`, `/verify-ownership`, `/verify-similarity`)*
- [ ] ⟳ **B2.3** `HashingService` wrapper + error mapping: service down → 502, timeout → 504,
      model not loaded → 503. Never surface an axios stack trace
- [ ] ✚ **B2.4** **`assetId` is ours.** T2 generates the UUID v7 and passes it at index time;
      T3 must never invent an identifier T2 has to map back. Assert this in the client's types
      so a contract regression fails at compile time

## Epic 3 — IPFS / Pinata (`IpfsModule`)

- [ ] **B3.1** Pinata client: `pinFile()` + `pinJSON()`
- [ ] **B3.2** ERC-721 metadata builder → metadata URI. Agree the `attributes` list with the
      Epic 6 owner **before** building
- [ ] ✚ **B3.3** `unpin()` — the compensating action for the `pinning_metadata` and `minting`
      failure branches of the saga. Without it, every failed mint leaks a pin

## Epic 4 — Auth (`AuthModule`) — Flow 1

- [ ] **B4.1** `GET /auth/nonce?address=` — random nonce, 5-min TTL, SIWE message. Add the
      expiry sweep now; an unbounded challenge table is a slow leak
- [ ] **B4.2** `POST /auth/login` — `ethers.verifyMessage`, recover, **compare to the address
      the nonce was issued to** (not the request body), set `consumed_at`, upsert `users`
- [ ] **B4.3** JWT issuance + `JwtStrategy` + `JwtAuthGuard`
- [ ] **B4.4** `GET /auth/me` + apply the guard per BD.4. `/verify/*` and `GET /nft/:tokenId`
      stay public

## Epic 5 — Image (`ImageModule`) — Flow 2, leg 1

- [ ] **B5.1** `POST /images/upload` — multer, size limit from config. Validate by **content
      sniffing**; a `.exe` renamed `.png` must be rejected
- [ ] ⟳ **B5.2** Orchestration: file → `HashingService.hash()` → persist `asset_fingerprints`
      → return `phash_bytes32` for the client to sign.
      **`bit_length` differs per algorithm** (dhash /72, hsv /42, phash /63) — hardcoding 64
      corrupts every distance downstream and no backend test would catch it
- [ ] ⟳ **B5.3** Duplicate pre-check: **`isHashRegistered(pHash)` only** — a free view call,
      no Epic 1 dependency. The URI does not exist until after pinning, so `isURIRegistered`
      cannot be pre-checked. Return the result as **advisory**; the contract revert is the
      only real guard
- [ ] **B5.4** DTOs + Swagger for Epic 5

## Epic 6 — Mint (`NftModule`) — Flow 2, leg 2 — ⟳ reshaped

- [ ] **B6.1** Pin image → build metadata → pin → `mintAsset()` → parse `tokenId` from
      `AssetMinted`
- [ ] ⟳ **B6.2** ~~`HashingService.sign(pHash)`~~ → **verify the client's signature locally
      with `verifyMessage` and assert it recovers to the JWT's address**, then split r/s/v and
      call `registerSignature()`. Verifying before submitting is the only thing between a
      malformed signature and a permanently unverifiable asset — the contract does not check
- [ ] ⟳ **B6.3** `POST /nft/mint` chaining B6.1 + B6.2 with `idempotency_key`. **Not
      transactional** — `mintAsset` cannot be rolled back. Forward-only recovery per
      [DESIGN.md §4.3](./DESIGN.md)
- [ ] ⟳ **B6.4** `GET /nft/:tokenId` — `tokenURI` + `creatorOf` + `ownerOf` + `isRegistered`,
      read **live**. Where `creatorOf` and the registered `creator` disagree, render the
      registered one and flag the asset (caveat 3)
- [ ] ⟳ **B6.5** ~~`POST /nft/:tokenId/transfer`~~ → **transfer is a client-side transaction.**
      The service wallet is never the owner, so `transferAsset` reverts for us; requiring
      `approve()` would be a custody model we should not want. Backend work here is a
      read-only endpoint returning what the client needs to build the tx, plus reconciliation
      from the `Transfer` event
- [ ] **B6.6** NFT DTOs + Swagger
- [ ] ✚ **B6.7** **`unregisterable` terminal saga state** — a token whose id was pre-registered
      by a third party (caveat 1) can never carry its proof. Distinct from `orphaned`, which
      *is* recoverable. The resume worker must not retry it forever, and BD.7 must define what
      the user sees

## Epic 7 — Verification (`SignatureModule`) — Flow 5

- [ ] ⟳ **B7.1** `POST /verify/ownership` — image → `/hash` → `verifySignatureView`.
      **`verifySignatureView` is a view that can revert.** Map three outcomes the contract
      collapses into two reverts and a boolean:
      `revert "token not registered"` → `unregistered` ·
      `revert ECDSAInvalidSignature*` → `malformed` ·
      `false` → `mismatch` · `true` → `verified`.
      Letting the revert surface as a 500 is wrong on every count
- [ ] ⟳ **B7.2** `POST /verify/similarity` — proxy to T3 `/similarity`, join `assetId` back to
      token/owner data, persist `similarity_score` **and `model_version`**
- [ ] **B7.3** `GET /signature/:tokenId` → decoded `getAssetSignature()` — display cache only
- [ ] ✚ **B7.4** Persist every verification to `verifications` (both kinds). This is access
      pattern A9 and the only queryable record — the on-chain event cannot be filtered by
      requester or date

## Epic 8 — Persistence

- [x] **B8.0** ✅ Decided: Postgres + Prisma
- [ ] **B8.1** `PrismaModule` + `PrismaService` + run the initial migration. The schema is
      already written; follow the prepend/append workflow at the top of `sql/init.sql` or the
      CHECK constraints and partial indexes are silently dropped on the next `migrate dev`.
      *Blocked on B0.9.*
- [ ] **B8.2** Repository layer + `/dashboard`. **Keyset pagination on `(created_at, id)`**,
      not `OFFSET`; `EXPLAIN` must show an index scan
- [ ] **B8.3** `mint_jobs` saga persistence + resume worker recovering `orphaned` jobs on boot
- [ ] ⟳ **B8.4** Chain indexer — poll the **standard ERC-721 `Transfer` event** plus
      `AssetRegistered`, from `chain_sync_cursor`, idempotent on `(tx_hash, log_index)`,
      ~30-block reorg lag.
      **Do not subscribe to `AssetTransferred`** — it is emitted only by the optional
      `transferAsset` wrapper, so every wallet and marketplace transfer would be missed and
      `owner_address` would desync silently. `Transfer` from `address(0)` is the mint
- [ ] ✗ **B8.5** ~~Similarity candidate search over `phash64`~~ — **removed.** The index lives
      in T3, keyed on `assetId`. `asset_fingerprints` is kept for audit and reproducibility,
      not for search

## Epic 9 — Testing

- [ ] **B9.1** Unit tests for `BlockchainModule` utils (mock ethers) — including the signing
      prefix trap from B1.4
- [ ] ⟳ **B9.2** Unit tests for `HashingService` + `IpfsService` (mock HTTP). Cover the
      **error mappings**, not just happy paths — they have no integration coverage until T3 is
      contract-compliant
- [ ] **B9.3** E2E for auth, mint, verify (mocked chain + T3)
- [ ] ✚ **B9.4** **Three non-negotiable specs**, regardless of what Epic 9 formally assigns —
      Auth, Image and the repository layer currently have no assigned coverage:
      1. nonce replay rejected **inside** the TTL (B4.2)
      2. content-sniff rejection of a disguised upload (B5.1)
      3. `bit_length` correct per algorithm (B5.2)

## Epic 10 — DevOps

- [ ] **B10.1** `Dockerfile` (multi-stage, Node 20)
- [ ] ⟳ **B10.2** Extend `compose.yaml` with the backend service — Postgres already added in
      B0.9
- [ ] ⟳ **B10.3** CI: lint + test + build for **backend and contracts**. Only hashing has a
      workflow today
- [ ] **B10.4** Rewrite `backend/README.md` with the real endpoints

---

## Suggested order

```
BD.4 + BD.8 + BD.9  →  B0.1–B0.4  →  B0.9  →  B8.1  →  B0.5, B0.7, B0.8, B0.10
                                                    ↓
                         B0.6  ←────────────────  BD.4 agreed
                                                    ↓
                            Epic 4  ∥  Epic 2 + Epic 3
                                                    ↓
                            Epic 5  →  Epic 6 / 7  →  B8.2–B8.4
                                                    ↓
                                        Epic 9  →  Epic 10
```

Three ordering constraints that are not obvious:

1. **B0.9 before B8.1.** The schema is written but has never been migrated, and there is no
   database to migrate it into.
2. **B8.1 before Epic 4 and Epic 5.** `/auth/login` writes `users`; every image endpoint
   writes `assets`. Neither can be built against a schema that does not exist.
3. **BD.8 before Epic 2.** Building a client for endpoints that do not exist, to a README
   that is wrong, produces work that has to be thrown away.

## Slice ownership

| Mine (platform / off-chain) | Not mine |
|---|---|
| Epic 0 · Epic 2 · Epic 3 · Epic 4 · Epic 5 | Epic 1 — blockchain layer |
| `B8.1`, `B8.2` · `B9.2`, `B9.4` | Epic 6 — mint saga · Epic 7 — verification |
| `BD.4`, `BD.8` | `B8.3`, `B8.4` · `B9.1`, `B9.3` · Epic 10 |
| | `BD.9` — escalation, but I raised it |

With BD.5 resolved and B5.3 reduced to a free view call, **this slice now has no blocking
dependency on Epic 1.** The only external blocker left is BD.8 — the T3 contract.
