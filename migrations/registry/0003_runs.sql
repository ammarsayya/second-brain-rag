-- 0003 run ledger (T-P1-08; docs/21 §1, NFR-07). One row per stateful CLI or worker invocation.

CREATE TABLE run (
    run_id       TEXT PRIMARY KEY CHECK (run_id GLOB 'run_*'),
    command      TEXT NOT NULL,
    config_hash  TEXT,
    code_version TEXT NOT NULL,
    git_sha      TEXT,
    pid          INTEGER NOT NULL,
    started_at   TEXT NOT NULL,
    ended_at     TEXT,
    status       TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'interrupted')),
    exit_code    INTEGER,
    error_class  TEXT,
    counts       TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(counts))
) STRICT;
CREATE INDEX run_started ON run (started_at);

CREATE TRIGGER run_no_delete BEFORE DELETE ON run
BEGIN
    SELECT RAISE(ABORT, 'run ledger rows are never deleted');
END;

CREATE TRIGGER run_finished_immutable BEFORE UPDATE ON run
WHEN OLD.status <> 'running'
BEGIN
    SELECT RAISE(ABORT, 'finished runs are immutable');
END;

-- activity.run_id (added in 0001 without a foreign key) must name a recorded run.
CREATE TRIGGER activity_run_exists BEFORE INSERT ON activity
WHEN NEW.run_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM run WHERE run_id = NEW.run_id)
BEGIN
    SELECT RAISE(ABORT, 'activity.run_id references an unknown run');
END;
