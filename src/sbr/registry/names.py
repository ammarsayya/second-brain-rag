"""Display-name repair for mojibake paths (T-P2-13, docs/03 §"File-name encoding").

A real corpus fact (docs/03, docs/37): a minority of paths (228 at the t0
baseline, 306 at t2/t3) are proper Unicode filenames that were mangled into
CP437/CP850/CP1252 mojibake at some earlier point in their history — an
archive extracted with the wrong codepage, a filesystem copy through a tool
that assumed the wrong encoding — e.g. ``Fl├ñche`` for ``Fläche`` (docs/08
§7's own example). :func:`repair_mojibake` detects and repairs this *only for
display*: the observed path itself (``PathObservation.relpath``/
``relpath_raw``) is never rewritten (HC-01 — a derived field is repaired, not
the evidence), and correction only ever touches
:class:`~sbr.schemas.registry.PathObservation.display_name`.

This is the same detector T-P2-08's archive inventory (:mod:`sbr.registry.archives`)
already needed for member names extracted from a codepage-ambiguous ZIP —
promoted here as the shared, general implementation (:mod:`archives` now
imports it) rather than duplicated, since both are the exact same repair
problem applied to different sources of names (an archive member's stored
name vs. a scanned filesystem entry's name).

**Why detection is telltale-gated, not a blind round trip**: Python's
``zipfile`` already decodes a non-UTF-8-flagged ZIP entry name using CP437
per the ZIP spec, which is *correct* for the common case. Blindly
re-encoding an already-correct name as CP437 and re-decoding it as UTF-8
does **not** detect mojibake — it destroys already-correct names into
different, still-printable-but-wrong characters (e.g. ``Ü`` becomes ``š``).
:func:`repair_mojibake` therefore only attempts a repair when the name
already contains one of a small set of byte sequences (:data:`MOJIBAKE_TELLTALES`)
that are essentially only ever produced by a genuine UTF-8-read-as-a-
single-byte-codepage mistake, never as a blind guess on a name with no such
evidence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from sbr import __version__
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.provenance import ProvenanceStore
from sbr.schemas.registry import ObservationState

NAMES_PRODUCER: Final = "sbr.registry.names"
NAMES_STAGE: Final = "names"

# Byte sequences that are essentially only ever produced by a genuine UTF-8-read-as-CP437/CP850/CP1252 mistake
# (docs/08 §7's own example: "Fl├ñche" for "Fläche"). Never a blind encode/decode round trip on a name with no
# such evidence — see the module docstring for why that would destroy already-correct names instead.
MOJIBAKE_TELLTALES: Final = ("Ã", "â€", "Â", "├", "â")

_SOURCE_ENCODINGS: Final = ("cp437", "cp850", "cp1252")


def repair_mojibake(name: str) -> str:
    """Repair one display-only mojibake name, or return it unchanged if there is no telltale evidence."""
    if not any(telltale in name for telltale in MOJIBAKE_TELLTALES):
        return name
    for source_encoding in _SOURCE_ENCODINGS:
        try:
            raw = name.encode(source_encoding)
            repaired = raw.decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if repaired != name and repaired.isprintable():
            return repaired
    return name


def repair_relpath_display(relpath: str) -> str:
    """Repair mojibake in EVERY segment of a full relpath, not just the leaf — for any consumer (citations,
    reports) that needs a readable full path, not just a readable filename.

    Found checking this task's own acceptance criterion against the real corpus: the census this task's
    acceptance criterion refers to (docs/03: "228 paths contain CP437 mojibake", 306 at the t2/t3 baseline,
    docs/37) counts a telltale ANYWHERE in the path — and on the real corpus, every one of those 306 cases has
    the corruption in an ANCESTOR FOLDER name, not the file's own leaf name (e.g. an entire folder named
    "Fehlersuche mittels Fl├ñche RL 9.11.06" containing otherwise correctly-named files). ``display_name``
    (repaired by :func:`repair_names` below) is documented (docs/31) as the leaf-name-only field on
    ``PathObservation`` and stays scoped to that — repairing it in place to mean "the whole path" would be a
    schema reinterpretation, not this task's call to make unilaterally. This function is the general-purpose
    full-path counterpart: pure, and independent of the registry, for whichever later stage (T-P2-14's
    manifest report, citation rendering, ...) chooses to use it.
    """
    return "\\".join(repair_mojibake(segment) for segment in relpath.split("\\"))


@dataclass(frozen=True, slots=True)
class NamesRunResult:
    activity_id: str
    considered: int
    repaired: int


def _utcnow() -> datetime:
    return datetime.now(UTC)


def repair_names(
    config: SbrConfig,
    db: RegistryDB,
    *,
    owner: str = "system:names-repair",
    clock: Callable[[], datetime] = _utcnow,
) -> NamesRunResult:
    """Recompute ``display_name`` for every currently-known PRESENT observation; ``relpath`` is never touched.

    Idempotent: an already-repaired (or never-corrupted) ``display_name`` has no mojibake telltale, so
    re-running finds nothing left to change and upserts nothing.
    """
    observations = db.repo(reg.PATH_OBSERVATION)
    considered = 0
    repaired = 0

    provenance = ProvenanceStore(db.conn, clock=clock)
    with provenance.activity(
        kind=NAMES_STAGE,
        producer=NAMES_PRODUCER,
        producer_version=__version__,
        agent=owner,
        params={},
    ) as activity:
        with transaction(db.conn):
            outputs: list[str] = []
            for obs in observations.find({"state": ObservationState.PRESENT}):
                considered += 1
                new_name = repair_mojibake(obs.display_name)
                if new_name == obs.display_name:
                    continue
                observations.upsert(
                    obs.model_copy(update={"display_name": new_name, "activity_id": activity.activity_id})
                )
                repaired += 1
                outputs.append(obs.obs_id)
        activity.outputs.extend(outputs)

    return NamesRunResult(activity_id=activity.activity_id, considered=considered, repaired=repaired)


__all__ = [
    "MOJIBAKE_TELLTALES",
    "NAMES_PRODUCER",
    "NAMES_STAGE",
    "NamesRunResult",
    "repair_mojibake",
    "repair_names",
    "repair_relpath_display",
]
