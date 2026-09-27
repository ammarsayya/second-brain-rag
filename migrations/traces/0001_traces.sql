-- 0001 trace store (T-P9-02; docs/07 section 8, HC-23). Separate from registry.sqlite.

CREATE TABLE span (
    span_id        TEXT PRIMARY KEY CHECK (span_id GLOB 'span_*'),
    run_id         TEXT NOT NULL CHECK (run_id GLOB 'run_*'),
    parent_span_id TEXT,
    sequence       INTEGER NOT NULL CHECK (sequence >= 0),
    kind           TEXT NOT NULL CHECK (kind IN ('node', 'tool_call', 'model_call')),
    name           TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 128),
    started_at     TEXT NOT NULL,
    ended_at       TEXT,
    duration_ms    REAL CHECK (duration_ms >= 0),
    status         TEXT NOT NULL CHECK (status IN ('running', 'ok', 'error', 'interrupted')),
    error_class    TEXT CHECK (error_class IS NULL OR length(error_class) BETWEEN 1 AND 128),
    inputs         TEXT CHECK (inputs IS NULL OR json_valid(inputs)),
    prompt_version TEXT CHECK (prompt_version IS NULL OR length(prompt_version) BETWEEN 1 AND 128),
    model           TEXT CHECK (model IS NULL OR length(model) BETWEEN 1 AND 128),
    raw_output      TEXT CHECK (raw_output IS NULL OR json_valid(raw_output)),
    parsed_output   TEXT CHECK (parsed_output IS NULL OR json_valid(parsed_output)),
    decision        TEXT CHECK (decision IS NULL OR json_valid(decision)),
    tool_calls      TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(tool_calls) AND json_type(tool_calls) = 'array'),
    cost_usd        REAL CHECK (cost_usd >= 0),
    input_tokens    INTEGER CHECK (input_tokens >= 0),
    output_tokens   INTEGER CHECK (output_tokens >= 0),
    UNIQUE (run_id, sequence),
    UNIQUE (run_id, span_id),
    FOREIGN KEY (run_id, parent_span_id) REFERENCES span (run_id, span_id),
    CHECK (
        (status = 'running' AND ended_at IS NULL AND duration_ms IS NULL AND error_class IS NULL)
        OR
        (status <> 'running' AND ended_at IS NOT NULL AND duration_ms IS NOT NULL)
    ),
    CHECK (status IN ('error', 'interrupted') OR error_class IS NULL)
) STRICT;

CREATE INDEX span_run_parent ON span (run_id, parent_span_id, sequence);

CREATE TRIGGER span_no_delete BEFORE DELETE ON span
BEGIN
    SELECT RAISE(ABORT, 'trace spans are never deleted');
END;

CREATE TRIGGER span_finished_immutable BEFORE UPDATE ON span
WHEN OLD.status <> 'running'
BEGIN
    SELECT RAISE(ABORT, 'finished trace spans are immutable');
END;
