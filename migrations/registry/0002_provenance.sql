-- 0002 provenance core (T-P1-07; docs/05 §2/§5 PV-1, HC-04).
-- * derived_from links (entity -> source entity, optional locator, role), attributed to an activity.
-- * Every write of a provenance-bearing row must name an existing activity that is still RUNNING.
-- * Finished activities are immutable; activities and derived_from links are never deleted.

CREATE TABLE derived_from (
    entity_id        TEXT NOT NULL,
    source_entity_id TEXT NOT NULL,
    role             TEXT NOT NULL CHECK (role IN ('primary', 'context', 'twin', 'evidence')),
    locator          TEXT CHECK (locator IS NULL OR json_valid(locator)),
    activity_id      TEXT NOT NULL REFERENCES activity (activity_id),
    PRIMARY KEY (entity_id, source_entity_id, role),
    CHECK (entity_id <> source_entity_id)
) STRICT;
CREATE INDEX derived_from_source ON derived_from (source_entity_id);

-- Activity lifecycle: running -> succeeded | failed | cancelled, once. Identity columns never change.
CREATE TRIGGER activity_no_delete BEFORE DELETE ON activity
BEGIN
    SELECT RAISE(ABORT, 'provenance: activities are never deleted');
END;

CREATE TRIGGER activity_finished_immutable BEFORE UPDATE ON activity
WHEN OLD.status <> 'running'
BEGIN
    SELECT RAISE(ABORT, 'provenance: finished activities are immutable');
END;

CREATE TRIGGER activity_identity_immutable BEFORE UPDATE ON activity
WHEN NEW.activity_id IS NOT OLD.activity_id OR NEW.kind IS NOT OLD.kind OR NEW.producer IS NOT OLD.producer
  OR NEW.producer_version IS NOT OLD.producer_version OR NEW.params_hash IS NOT OLD.params_hash
  OR NEW.agent IS NOT OLD.agent OR NEW.run_id IS NOT OLD.run_id OR NEW.started_at IS NOT OLD.started_at
  OR NEW.inputs IS NOT OLD.inputs
BEGIN
    SELECT RAISE(ABORT, 'provenance: activity identity columns are immutable');
END;

CREATE TRIGGER activity_must_start_running BEFORE INSERT ON activity
WHEN NEW.status <> 'running' OR NEW.ended_at IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'provenance: activities are recorded as running and finished later');
END;

CREATE TRIGGER derived_from_no_delete BEFORE DELETE ON derived_from
BEGIN
    SELECT RAISE(ABORT, 'provenance: derived_from links are never deleted');
END;

CREATE TRIGGER derived_from_no_update BEFORE UPDATE ON derived_from
BEGIN
    SELECT RAISE(ABORT, 'provenance: derived_from links are immutable');
END;

-- Writes require a running activity (TS-PROV-1). One insert and one update trigger per provenance-bearing table.
CREATE TRIGGER derived_from_requires_activity BEFORE INSERT ON derived_from
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN
    SELECT RAISE(ABORT, 'provenance: write requires a running activity');
END;

CREATE TRIGGER scan_ins_requires_activity BEFORE INSERT ON scan
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;
CREATE TRIGGER scan_upd_requires_activity BEFORE UPDATE ON scan
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;

CREATE TRIGGER blob_ins_requires_activity BEFORE INSERT ON blob
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;
CREATE TRIGGER blob_upd_requires_activity BEFORE UPDATE ON blob
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;

CREATE TRIGGER path_observation_ins_requires_activity BEFORE INSERT ON path_observation
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;
CREATE TRIGGER path_observation_upd_requires_activity BEFORE UPDATE ON path_observation
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;

CREATE TRIGGER archive_member_ins_requires_activity BEFORE INSERT ON archive_member
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;
CREATE TRIGGER archive_member_upd_requires_activity BEFORE UPDATE ON archive_member
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;

CREATE TRIGGER blob_classification_ins_requires_activity BEFORE INSERT ON blob_classification
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;
CREATE TRIGGER blob_classification_upd_requires_activity BEFORE UPDATE ON blob_classification
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;

CREATE TRIGGER blob_relation_ins_requires_activity BEFORE INSERT ON blob_relation
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;
CREATE TRIGGER blob_relation_upd_requires_activity BEFORE UPDATE ON blob_relation
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;

CREATE TRIGGER change_event_ins_requires_activity BEFORE INSERT ON change_event
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;
CREATE TRIGGER change_event_upd_requires_activity BEFORE UPDATE ON change_event
WHEN (SELECT status FROM activity WHERE activity_id = NEW.activity_id) IS NOT 'running'
BEGIN SELECT RAISE(ABORT, 'provenance: write requires a running activity'); END;
