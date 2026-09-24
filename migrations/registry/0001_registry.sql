-- 0001 registry core (T-P1-06; docs/31 §1, docs/32 §1). STRICT tables; every derived row names its producing activity.

CREATE TABLE activity (
    activity_id      TEXT PRIMARY KEY CHECK (activity_id GLOB 'act_*'),
    kind             TEXT NOT NULL,
    producer         TEXT NOT NULL,
    producer_version TEXT NOT NULL,
    params_hash      TEXT,
    agent            TEXT NOT NULL CHECK (agent GLOB 'system:*' OR agent GLOB 'model:*/*@*' OR agent = 'user:owner'),
    run_id           TEXT,
    started_at       TEXT NOT NULL,
    ended_at         TEXT,
    status           TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'cancelled')),
    inputs           TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(inputs)),
    outputs          TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(outputs)),
    notes            TEXT
) STRICT;
CREATE INDEX activity_kind ON activity (kind, started_at);

CREATE TABLE source_root (
    root_id   TEXT PRIMARY KEY,
    path      TEXT NOT NULL,
    kind      TEXT NOT NULL CHECK (kind IN ('university', 'external_accepted', 'personal', 'quarantine')),
    read_only INTEGER NOT NULL CHECK (read_only IN (0, 1)),
    added_at  TEXT NOT NULL,
    CHECK (kind = 'quarantine' OR read_only = 1)
) STRICT;

CREATE TABLE scan (
    scan_id      TEXT PRIMARY KEY CHECK (scan_id GLOB 'scan_*'),
    root_id      TEXT NOT NULL REFERENCES source_root (root_id),
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    status       TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'interrupted')),
    files_seen   INTEGER NOT NULL DEFAULT 0 CHECK (files_seen >= 0),
    bytes_seen   INTEGER NOT NULL DEFAULT 0 CHECK (bytes_seen >= 0),
    errors       INTEGER NOT NULL DEFAULT 0 CHECK (errors >= 0),
    code_version TEXT NOT NULL,
    activity_id  TEXT NOT NULL REFERENCES activity (activity_id)
) STRICT;

CREATE TABLE blob (
    blob_id          TEXT PRIMARY KEY CHECK (blob_id GLOB 'b3:*' AND length(blob_id) = 67),
    size             INTEGER NOT NULL CHECK (size >= 0),
    magic_type       TEXT,
    format           TEXT,
    knowledge_class  TEXT NOT NULL,
    sensitivity      TEXT NOT NULL CHECK (sensitivity IN ('normal', 'personal', 'third_party_personal', 'restricted')),
    status           TEXT NOT NULL CHECK (status IN ('active', 'orphaned', 'excluded')),
    first_seen_scan  TEXT NOT NULL REFERENCES scan (scan_id),
    last_seen_scan   TEXT NOT NULL REFERENCES scan (scan_id),
    hash_mode        TEXT NOT NULL CHECK (hash_mode IN ('full', 'full_lowprio_pending')),
    canonical_obs_id TEXT,
    activity_id      TEXT NOT NULL REFERENCES activity (activity_id)
) STRICT;

CREATE TABLE path_observation (
    obs_id              TEXT PRIMARY KEY CHECK (obs_id GLOB 'obs_*'),
    root_id             TEXT NOT NULL REFERENCES source_root (root_id),
    relpath             TEXT NOT NULL,
    relpath_raw         TEXT NOT NULL,
    display_name        TEXT NOT NULL,
    blob_id             TEXT REFERENCES blob (blob_id),
    size                INTEGER NOT NULL CHECK (size >= 0),
    mtime_ns            INTEGER NOT NULL CHECK (mtime_ns >= 0),
    first_seen_scan     TEXT NOT NULL REFERENCES scan (scan_id),
    last_seen_scan      TEXT NOT NULL REFERENCES scan (scan_id),
    state               TEXT NOT NULL CHECK (state IN ('present', 'moved', 'deleted')),
    in_archive          TEXT REFERENCES path_observation (obs_id),
    folder_tokens       TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(folder_tokens)),
    is_mirror_candidate INTEGER NOT NULL DEFAULT 0 CHECK (is_mirror_candidate IN (0, 1)),
    activity_id         TEXT NOT NULL REFERENCES activity (activity_id)
) STRICT;
-- At most one *present* observation per path; history rows (moved/deleted) are kept.
CREATE UNIQUE INDEX path_observation_present ON path_observation (root_id, relpath) WHERE state = 'present';
CREATE INDEX path_observation_blob ON path_observation (blob_id);

CREATE TABLE archive_member (
    container_blob      TEXT NOT NULL REFERENCES blob (blob_id),
    member_path         TEXT NOT NULL,
    member_name_display TEXT NOT NULL,
    member_size         INTEGER NOT NULL CHECK (member_size >= 0),
    member_blob         TEXT,
    status              TEXT NOT NULL CHECK (status IN ('already_present', 'extracted_new', 'skipped_limit', 'excluded')),
    extracted_path      TEXT,
    activity_id         TEXT NOT NULL REFERENCES activity (activity_id),
    PRIMARY KEY (container_blob, member_path)
) STRICT;

CREATE TABLE blob_classification (
    blob_id           TEXT NOT NULL REFERENCES blob (blob_id),
    genre             TEXT,
    genre_confidence  REAL CHECK (genre_confidence BETWEEN 0 AND 1),
    course_id         TEXT,
    course_confidence REAL CHECK (course_confidence BETWEEN 0 AND 1),
    language_guess    TEXT,
    semester          TEXT,
    institution       TEXT,
    isbn              TEXT,
    rules_version     TEXT NOT NULL,
    activity_id       TEXT NOT NULL REFERENCES activity (activity_id),
    PRIMARY KEY (blob_id, rules_version)
) STRICT;

CREATE TABLE blob_relation (
    src_blob    TEXT NOT NULL REFERENCES blob (blob_id),
    dst_blob    TEXT NOT NULL REFERENCES blob (blob_id),
    type        TEXT NOT NULL,
    confidence  REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    evidence    TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(evidence)),
    status      TEXT NOT NULL CHECK (status IN ('candidate', 'confirmed', 'rejected')),
    activity_id TEXT NOT NULL REFERENCES activity (activity_id),
    PRIMARY KEY (src_blob, dst_blob, type),
    CHECK (src_blob <> dst_blob)
) STRICT;

CREATE TABLE change_event (
    event_id    INTEGER PRIMARY KEY,
    scan_id     TEXT NOT NULL REFERENCES scan (scan_id),
    type        TEXT NOT NULL CHECK (type IN ('new', 'alias', 'moved', 'modified', 'deleted')),
    obs_id      TEXT NOT NULL REFERENCES path_observation (obs_id),
    blob_id     TEXT,
    details     TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(details)),
    activity_id TEXT NOT NULL REFERENCES activity (activity_id)
) STRICT;
CREATE INDEX change_event_scan ON change_event (scan_id);
