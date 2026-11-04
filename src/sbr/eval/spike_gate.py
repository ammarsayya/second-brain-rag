"""Sensitivity gate shared by the evaluation/spike tools that open source *content* (docs/22 §3).

Spike tools read registry blobs directly instead of going through a pipeline stage, so each one used to
decide on its own which blobs it may open.  This module gives them one rule: only blobs that
:func:`sbr.registry.sensitivity.local_processing_allowed` admits, judged on every current alias.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from collections.abc import Collection, Iterable

from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.registry.sensitivity import local_processing_allowed
from sbr.schemas import BlobRecord, PathObservation

__all__ = ["processable_blobs"]


def processable_blobs(
    db: RegistryDB,
    observations: Iterable[PathObservation],
    formats: Collection[str],
) -> dict[str, BlobRecord]:
    """Return ``blob_id -> blob`` for blobs of ``formats`` whose content may be processed locally.

    The number of gated-out blobs is reported on stderr as a count only; their paths are never printed.
    """
    aliases: dict[str, list[str]] = defaultdict(list)
    for observation in observations:
        if observation.blob_id is not None:
            aliases[observation.blob_id].append(observation.relpath)
    allowed: dict[str, BlobRecord] = {}
    skipped = 0
    for blob in db.repo(reg.BLOB).find():
        if blob.format not in formats:
            continue
        if local_processing_allowed(blob.status, blob.sensitivity, aliases.get(blob.blob_id, [])):
            allowed[blob.blob_id] = blob
        else:
            skipped += 1
    if skipped:
        print(f"sensitivity gate: {skipped} blob(s) not opened (status/sensitivity)", file=sys.stderr)
    return allowed
