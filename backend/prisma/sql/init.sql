-- B8.1 — DDL that Prisma cannot express declaratively.
--
-- Workflow:
--   npx prisma migrate dev --create-only --name init
--   -> open prisma/migrations/<timestamp>_init/migration.sql
--   -> PREPEND section A (the uuidv7 shim must exist before any table defaults to it)
--   -> APPEND sections B and C
--   npx prisma migrate dev
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

ALTER TABLE asset_signatures
  ADD CONSTRAINT asset_signatures_signer_address_format
  CHECK (signer_address ~ '^0x[0-9a-fA-F]{40}$'),
  -- bytes32 on chain: exactly 32 bytes, no more, no less.
  ADD CONSTRAINT asset_signatures_hash_length CHECK (octet_length(perceptual_hash) = 32),
  ADD CONSTRAINT asset_signatures_r_length     CHECK (octet_length(sig_r) = 32),
  ADD CONSTRAINT asset_signatures_s_length     CHECK (octet_length(sig_s) = 32),
  ADD CONSTRAINT asset_signatures_v_range      CHECK (sig_v IN (27, 28));

ALTER TABLE verifications
  ADD CONSTRAINT verifications_requester_address_format
  CHECK (requester_address IS NULL OR requester_address ~ '^0x[0-9a-fA-F]{40}$'),
  -- Each kind fills a different result column. Enforce it here rather than trusting
  -- every write path to remember.
  ADD CONSTRAINT verifications_result_shape CHECK (
    (kind = 'ownership'  AND similarity_score IS NULL)
    OR
    (kind = 'similarity' AND result IS NULL AND token_id IS NULL)
  );

ALTER TABLE chain_sync_cursor
  ADD CONSTRAINT chain_sync_cursor_address_format
  CHECK (contract_address ~ '^0x[0-9a-fA-F]{40}$');

-- phash64 is only meaningful for the phash algorithm; bit_length must be positive.
ALTER TABLE asset_fingerprints
  ADD CONSTRAINT asset_fingerprints_phash64_scope
  CHECK ((algorithm = 'phash') OR (phash64 IS NULL)),
  ADD CONSTRAINT asset_fingerprints_bit_length_positive
  CHECK (bit_length > 0);


-- ===========================================================================
-- C. APPEND — partial indexes
-- ===========================================================================

-- The resume worker's only query (DESIGN.md §5). Partial, so it stays tiny no matter
-- how many completed jobs accumulate.
CREATE INDEX mint_jobs_resumable_idx
  ON mint_jobs (updated_at)
  WHERE status IN ('running', 'stalled', 'orphaned');

-- Candidate generation for B8.5 scans this column; excluding NULLs keeps the scan to
-- rows that actually carry a canonical hash.
CREATE INDEX asset_fingerprints_phash64_idx
  ON asset_fingerprints (phash64)
  WHERE phash64 IS NOT NULL;

-- Unconsumed, unexpired challenges — the only nonces /auth/login should ever match.
CREATE INDEX auth_nonces_live_idx
  ON auth_nonces (address, expires_at)
  WHERE consumed_at IS NULL;

-- NOTE: the popcount search itself cannot use a btree —
--   ORDER BY bit_count(phash64 # :query) LIMIT 50
-- is a sequential scan by design, which DESIGN.md §8 accepts to ~10^5 assets. The index
-- above only serves exact-match lookups (the duplicate pre-check in B5.3).


-- ===========================================================================
-- D. Seed — indexer cursors
-- ===========================================================================
-- Replace the deployment blocks before running. Starting at 0 forces the indexer to
-- replay the entire chain from genesis on first boot.

INSERT INTO chain_sync_cursor (contract_name, contract_address, last_processed_block, updated_at)
VALUES
  ('DAMAsset',     '0xE7127207eB3E24B34021344aCB7D7Cff5D092A59', 0, now()),
  ('DAMSignature', '0xA55Ba1468967ad3a11adD593eA702673cc66d660', 0, now()),
  ('DAMVerifier',  '0x1524c7e44fDad13f4288b36Fca468647002DbecF', 0, now())
ON CONFLICT (contract_name) DO NOTHING;
