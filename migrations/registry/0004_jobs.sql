-- 0004 job queue (T-P1-09; docs/08 §2, HC-16, HC-24, NFR-02, NFR-03).
-- Idempotency key: (subject_id, stage, stage_version). A lease is identified by a unique token; only the holder of
-- the current token can complete or fail the item, so a re-leased item can never be completed twice.

CREATE TABLE work_item (
    job_id             TEXT PRIMARY KEY CHECK (job_id GLOB 'job_*'),
    subject_id         TEXT NOT NULL,
    stage              TEXT NOT NULL,
    stage_version      TEXT NOT NULL,
    state              TEXT NOT NULL CHECK (state IN ('pending', 'leased', 'done', 'failed', 'skipped', 'stale')),
    priority           INTEGER NOT NULL DEFAULT 0,
    wave               TEXT,
    attempts           INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts       INTEGER NOT NULL CHECK (max_attempts >= 1),
    not_before_ms      INTEGER NOT NULL DEFAULT 0,
    lease_owner        TEXT,
    lease_token        TEXT,
    lease_expires_ms   INTEGER,
    last_error         TEXT,
    output_manifest_id TEXT,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    UNIQUE (subject_id, stage, stage_version),
    CHECK ((state = 'leased') = (lease_token IS NOT NULL AND lease_expires_ms IS NOT NULL AND lease_owner IS NOT NULL))
) STRICT;
CREATE INDEX work_item_ready ON work_item (stage, state, priority DESC, not_before_ms, created_at);
CREATE INDEX work_item_subject ON work_item (subject_id, stage);
CREATE INDEX work_item_leases ON work_item (state, lease_expires_ms);

CREATE TABLE work_output (
    manifest_id TEXT PRIMARY KEY CHECK (manifest_id GLOB 'man_*'),
    job_id      TEXT NOT NULL UNIQUE REFERENCES work_item (job_id),
    artifacts   TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(artifacts)),
    created_at  TEXT NOT NULL
) STRICT;

CREATE TRIGGER work_item_no_delete BEFORE DELETE ON work_item
BEGIN
    SELECT RAISE(ABORT, 'work items are never deleted (mark them stale or skipped)');
END;

CREATE TRIGGER work_output_no_delete BEFORE DELETE ON work_output
BEGIN
    SELECT RAISE(ABORT, 'work outputs are never deleted');
END;
