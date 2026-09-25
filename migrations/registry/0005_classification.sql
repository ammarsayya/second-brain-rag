-- 0005 file classification (T-P2-04; docs/28, docs/37 G3).
-- SQLite stores booleans as constrained integers; existing blobs are known-unencrypted until S4 classifies them.

ALTER TABLE blob ADD COLUMN encrypted INTEGER NOT NULL DEFAULT 0 CHECK (encrypted IN (0, 1));
