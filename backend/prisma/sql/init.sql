-- B8.1 — DDL that Prisma cannot express declaratively.
--
-- Workflow:
--   npx prisma migrate dev --create-only --name init
--   -> open prisma/migrations/<timestamp>_init/migration.sql
--   -> PREPEND section A (the uuidv7 shim must exist before any table defaults to it)
--   -> APPEND sections B and C
--   npx prisma migrate dev
--
-- Section D is NOT part of the migration. See the warning there.
--
-- The `citext` extension is handled by the datasource `extensions = [citext]` block and
-- does not belong here.

-- ===========================================================================
-- A. PREPEND — uuidv7() compatibility shim
-- ===========================================================================
-- Postgres 18+ ships uuidv7() natively; this is a no-op there. On 16/17 it installs
-- the community PL/pgSQL implementation so `@default(dbgenerated("uuidv7()"))` resolves.
--
-- v7 over v4 is not cosmetic: v7 is time-ordered, so inserts append to the right edge
-- of the btree instead of scattering across it. On `assets` and `verifications`, which
-- are append-heavy, that is the difference between a healthy index and a bloated one.
-- It is also what makes `id` a sane keyset tiebreaker next to `created_at` (B8.2).

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'uuidv7' AND pronargs = 0
  ) THEN
    EXECUTE $fn$
      CREATE FUNCTION uuidv7() RETURNS uuid AS $body$
        SELECT encode(
          set_bit(
            set_bit(
              overlay(
                uuid_send(gen_random_uuid())
                PLACING substring(
                  int8send(floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint)
                  FROM 3
                )
                FROM 1 FOR 6
              ),
              52, 1
            ),
            53, 1
          ),
          'hex'
        )::uuid;
      $body$ LANGUAGE sql VOLATILE;
    $fn$;
  END IF;
END
$$;

-- Verify before trusting it. Both rows must report version 7:
--   SELECT uuidv7(), ('x' || substr(uuidv7()::text, 15, 1))::bit(4)::int AS version;
-- If version is not 7 on your Postgres build, drop the function and switch the four
-- @default(dbgenerated("uuidv7()")) in schema.prisma to gen_random_uuid(). Losing
-- time-ordering costs index locality, nothing correctness-critical.


-- ===========================================================================
-- B. APPEND — CHECK constraints
-- ===========================================================================
-- Prisma has no declarative CHECK. These are the invariants that keep garbage
-- addresses and impossible hashes out of the projection.

-- --- Address shape ---------------------------------------------------------
-- EIP-55-shaped addresses. citext makes the comparison case-insensitive; the CHECK
-- only constrains shape, never checksum.
ALTER TABLE users
  ADD CONSTRAINT users_wallet_address_format
  CHECK (wallet_address ~ '^0x[0-9a-fA-F]{40}$');

ALTER TABLE auth_nonces
  ADD CONSTRAINT auth_nonces_address_format
  CHECK (address ~ '^0x[0-9a-fA-F]{40}$');

ALTER TABLE assets
  ADD CONSTRAINT assets_creator_address_format
  CHECK (creator_address ~ '^0x[0-9a-fA-F]{40}$'),
  ADD CONSTRAINT assets_owner_address_format
  CHECK (owner_address ~ '^0x[0-9a-fA-F]{40}$');

ALTER TABLE chain_sync_cursor
  ADD CONSTRAINT chain_sync_cursor_address_format
  CHECK (contract_address ~ '^0x[0-9a-fA-F]{40}$');

-- --- Tx hash shape ---------------------------------------------------------
-- varchar(66), not char(66): bpchar pads with spaces and compares by different rules,
-- so a short write is padded silently instead of rejected. The CHECK is what actually
-- enforces the width. All nullable except where the row only exists post-confirmation.
ALTER TABLE assets
  ADD CONSTRAINT assets_mint_tx_hash_format
  CHECK (mint_tx_hash IS NULL OR mint_tx_hash ~ '^0x[0-9a-fA-F]{64}$'),
  ADD CONSTRAINT assets_signature_tx_hash_format
  CHECK (signature_tx_hash IS NULL OR signature_tx_hash ~ '^0x[0-9a-fA-F]{64}$');

ALTER TABLE mint_jobs
  ADD CONSTRAINT mint_jobs_mint_tx_hash_format
  CHECK (mint_tx_hash IS NULL OR mint_tx_hash ~ '^0x[0-9a-fA-F]{64}$'),
  ADD CONSTRAINT mint_jobs_signature_tx_hash_format
  CHECK (signature_tx_hash IS NULL OR signature_tx_hash ~ '^0x[0-9a-fA-F]{64}$');

ALTER TABLE asset_signatures
  ADD CONSTRAINT asset_signatures_tx_hash_format
  CHECK (tx_hash ~ '^0x[0-9a-fA-F]{64}$');

ALTER TABLE verifications
  ADD CONSTRAINT verifications_onchain_tx_hash_format
  CHECK (onchain_tx_hash IS NULL OR onchain_tx_hash ~ '^0x[0-9a-fA-F]{64}$');

ALTER TABLE processed_logs
  ADD CONSTRAINT processed_logs_tx_hash_format
  CHECK (tx_hash ~ '^0x[0-9a-fA-F]{64}$'),
  ADD CONSTRAINT processed_logs_log_index_nonneg
  CHECK (log_index >= 0);

-- --- Signature shape -------------------------------------------------------
-- bytes32 on chain: exactly 32 bytes, no more, no less. Applied twice, because the
-- signature lives on mint_jobs while the saga runs and on asset_signatures once the
-- chain confirms it.
ALTER TABLE asset_signatures
  ADD CONSTRAINT asset_signatures_signer_address_format
  CHECK (signer_address ~ '^0x[0-9a-fA-F]{40}$'),
  ADD CONSTRAINT asset_signatures_hash_length CHECK (octet_length(perceptual_hash) = 32),
  ADD CONSTRAINT asset_signatures_r_length     CHECK (octet_length(sig_r) = 32),
  ADD CONSTRAINT asset_signatures_s_length     CHECK (octet_length(sig_s) = 32),
  ADD CONSTRAINT asset_signatures_v_range      CHECK (sig_v IN (27, 28));

ALTER TABLE mint_jobs
  ADD CONSTRAINT mint_jobs_hash_length CHECK (octet_length(perceptual_hash) = 32),
  ADD CONSTRAINT mint_jobs_r_length    CHECK (octet_length(sig_r) = 32),
  ADD CONSTRAINT mint_jobs_s_length    CHECK (octet_length(sig_s) = 32),
  ADD CONSTRAINT mint_jobs_v_range     CHECK (sig_v IN (27, 28));

-- --- Verification shape ----------------------------------------------------
ALTER TABLE verifications
  ADD CONSTRAINT verifications_requester_address_format
  CHECK (requester_address IS NULL OR requester_address ~ '^0x[0-9a-fA-F]{40}$'),
  ADD CONSTRAINT verifications_submitted_hash_length
  CHECK (octet_length(submitted_hash) = 32),
  -- Each kind fills a different set of columns. The ownership branch is deliberately
  -- strict: verifySignatureView(tokenId, hash) cannot be called without a tokenId, and
  -- DESIGN.md §8.4 requires B7.1 to map every revert to a clean boolean rather than
  -- persisting an unknown. Loosen `result IS NOT NULL` only if that taxonomy grows its
  -- own column.
  ADD CONSTRAINT verifications_result_shape CHECK (
    (kind = 'ownership'
      AND token_id IS NOT NULL
      AND result IS NOT NULL
      AND similarity_score IS NULL)
    OR
    (kind = 'similarity'
      AND result IS NULL
      AND token_id IS NULL)
  );

ALTER TABLE verification_candidates
  ADD CONSTRAINT verification_candidates_rank_positive CHECK (rank > 0),
  ADD CONSTRAINT verification_candidates_score_range   CHECK (score >= 0 AND score <= 1),
  -- Squared L2 over unit-normalised embeddings is bounded by 4. A value outside that
  -- means T3 changed its metric or stopped normalising — fail loudly rather than
  -- silently reranking against a different space.
  ADD CONSTRAINT verification_candidates_ann_distance_range
  CHECK (ann_distance IS NULL OR (ann_distance >= 0 AND ann_distance <= 4));

-- --- Fingerprint shape -----------------------------------------------------
ALTER TABLE asset_fingerprints
  ADD CONSTRAINT asset_fingerprints_bit_length_positive
  CHECK (bit_length > 0),
  -- bits must actually hold bit_length bits. Catches the class of bug bit_length
  -- exists to prevent: a hash stored against the wrong denominator.
  ADD CONSTRAINT asset_fingerprints_bits_match_length
  CHECK (octet_length(bits) = ((bit_length + 7) / 8));


-- ===========================================================================
-- C. APPEND — partial indexes
-- ===========================================================================

-- The resume worker's only query (DESIGN.md §4.3). Partial, so it stays tiny no matter
-- how many completed jobs accumulate.
--
-- 'unregisterable' is deliberately NOT in this list. Per DESIGN.md §8.1 a token whose
-- id or pHash slot was griefed can never be registered — there is no admin path and no
-- upgrade proxy — so including it would make the worker retry forever.
CREATE INDEX mint_jobs_resumable_idx
  ON mint_jobs (updated_at)
  WHERE status IN ('running', 'stalled', 'orphaned');

-- Unconsumed, unexpired challenges — the only nonces /auth/login should ever match.
-- The expiry sweep is served by the plain (expires_at) index declared in schema.prisma;
-- this one cannot serve it, because it leads with `address`.
CREATE INDEX auth_nonces_live_idx
  ON auth_nonces (address, expires_at)
  WHERE consumed_at IS NULL;

-- Assets not yet in T3's similarity index — the backfill worker's queue. Partial, so it
-- is empty in the steady state. An asset stuck here is invisible to every similarity
-- search, which is a silent failure with no other detector.
CREATE INDEX assets_awaiting_t3_index_idx
  ON assets (created_at)
  WHERE indexed_in_t3_at IS NULL;

-- NOTE: there is no popcount / Hamming search index here, and there should not be.
-- B8.5 was removed: the similarity index lives in T3, keyed on the assetId this backend
-- supplies (DESIGN.md §6). asset_fingerprints is audit and reproducibility only
-- (DESIGN.md §7). The exact-duplicate pre-check is isHashRegistered() on chain — a free
-- view call — not a query against this database (B5.3).


-- ===========================================================================
-- D. Indexer cursors — NOT part of the migration
-- ===========================================================================
-- DO NOT append this section to migration.sql.
--
-- A migration is immutable, but contract addresses are not: redeploy the contracts and
-- a hardcoded seed becomes silently wrong while .env.example holds the right values.
-- Two sources of truth for the same fact, one of which cannot be corrected in place.
--
-- The indexer (B8.4) must upsert these at boot from DAM_ASSET_ADDRESS /
-- DAM_SIGNATURE_ADDRESS / DAM_VERIFIER_ADDRESS, with last_processed_block seeded to the
-- DEPLOYMENT block — not 0, which forces a replay from genesis on first boot.
--
-- Kept below only as a manual convenience for poking at a local database before B8.4
-- exists. Replace the block numbers before you use it.
--
-- INSERT INTO chain_sync_cursor (contract_name, contract_address, last_processed_block, updated_at)
-- VALUES
--   ('DAMAsset',     '0xE7127207eB3E24B34021344aCB7D7Cff5D092A59', 0, now()),
--   ('DAMSignature', '0xA55Ba1468967ad3a11adD593eA702673cc66d660', 0, now()),
--   ('DAMVerifier',  '0x1524c7e44fDad13f4288b36Fca468647002DbecF', 0, now())
-- ON CONFLICT (contract_name) DO NOTHING;
