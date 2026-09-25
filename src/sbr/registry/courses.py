"""Course and abbreviation mapping (T-P2-11).

Matches each blob's current folder path against the owner-curated
``curation/course_map.yaml`` (:class:`~sbr.curation.CourseMapEntry`), seeded
from the two authoritative taxonomy seeds at the corpus root
(``curriculum_mbi_ws2019.pdf``, ``MBI-WS2019-Modulhandbuch.pdf`` — docs/12
§"Seeds") and the real corpus's own folder abbreviations (Reg1, RGT, MSR2,
GrdInf, BS1, KONleh, ...). Metadata-only, like classification (T-P2-04),
sensitivity (T-P2-05) and genre (T-P2-10): this stage never opens a source
file, only :class:`~sbr.schemas.registry.PathObservation.folder_tokens`
(already NFC-normalized and casefolded by the scanner).

A course entry matches via two kinds of curated patterns, both compared as
contiguous runs of tokens against a file's ``folder_tokens``:

* ``aliases`` — a single folder-segment token (e.g. ``"Statik"``).
* ``folder_patterns`` — an ordered multi-segment relpath prefix (e.g.
  ``"Mechanical\\physik"``), used either to scope a short/reused token to one
  domain, or to give an entire subtree a broad default course.

Whichever matcher's *last* token lands deepest in a file's ``folder_tokens``
wins — so a more specific nested pattern (``"BachelorArbeit\\Praxisphase"``)
overrides a broader ancestor default (``"BachelorArbeit"``) for files under
it, the same "most specific wins" principle as genre's filename-only rule
(T-P2-10). A longer matcher breaks a tie over a shorter one at the same
depth; declaration order in the YAML breaks any remaining tie. A folder with
no matching alias or pattern resolves to ``course_id=None`` — an *explicit*
"unknown", not a gap: this task's acceptance criterion is "all level-3
folders mapped or marked unknown", and every unmatched folder already is
"marked unknown" by this default, reportable via ``tools/validate_courses.py``
for the owner to review and refine.

Confidence: 0.9 for a multi-segment ``folder_patterns`` match (an explicit,
domain-scoped decision), 0.75 for a single-token ``aliases`` match (a shorter,
more collision-prone signal on its own). Several aliases in the curated map
are themselves the owner's best guess from the module handbook rather than a
verified official abbreviation (documented per-entry in the YAML's comments)
and are deliberately encoded as plain ``aliases`` (0.75) rather than
``folder_patterns`` (0.9) so their lower certainty is visible in the score.

:class:`~sbr.schemas.registry.BlobClassification` is shared with genre's
output (T-P2-10) on the same primary key, ``(blob_id, rules_version)`` — this
stage always reads whatever row already exists for a blob first and copies
its other fields forward unchanged (rather than overwriting them with
defaults), since a naive upsert of a course-only record would blank out that
blob's genre/semester/isbn.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from sbr import __version__
from sbr.config import SbrConfig
from sbr.curation import CourseMapEntry, load_course_map
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.provenance import ProvenanceStore
from sbr.registry.genre import GENRE_RULES_VERSION
from sbr.schemas import BlobClassification, PathObservation
from sbr.schemas.registry import KnowledgeClass, ObservationState

COURSES_PRODUCER: Final = "sbr.registry.courses"
COURSES_STAGE: Final = "courses"
DEFAULT_COURSE_MAP_NAME: Final = "course_map.yaml"

PATTERN_CONFIDENCE: Final = 0.9
ALIAS_CONFIDENCE: Final = 0.75

_INELIGIBLE_KNOWLEDGE_CLASSES: Final = frozenset(
    {
        KnowledgeClass.TOOL_ARTIFACT,
        KnowledgeClass.CODE,
        KnowledgeClass.EXECUTABLE,
        KnowledgeClass.JUNK,
        KnowledgeClass.THIRD_PARTY_REFERENCE,
    }
)


@dataclass(frozen=True, slots=True)
class _Matcher:
    course_id: str
    tokens: tuple[str, ...]  # already casefolded
    confidence: float


@dataclass(frozen=True, slots=True)
class CourseDecision:
    course_id: str | None
    confidence: float | None


@dataclass(frozen=True, slots=True)
class CoursesRunResult:
    activity_id: str
    considered: int
    classified: int
    unknown: int


def _fold(token: str) -> str:
    return unicodedata.normalize("NFC", token).casefold()


def build_matchers(courses: Sequence[CourseMapEntry]) -> list[_Matcher]:
    """Flatten every course's aliases/folder_patterns into one ordered matcher list (declaration order kept)."""
    matchers: list[_Matcher] = []
    for entry in courses:
        for alias in entry.aliases:
            matchers.append(_Matcher(entry.course_id, (_fold(alias),), ALIAS_CONFIDENCE))
        for pattern in entry.folder_patterns:
            segments = tuple(_fold(part) for part in pattern.split("\\") if part)
            if segments:
                matchers.append(_Matcher(entry.course_id, segments, PATTERN_CONFIDENCE))
    return matchers


def _last_match_end(folder_tokens: list[str], pattern: tuple[str, ...]) -> int | None:
    """The end index (inclusive) of the LAST contiguous occurrence of ``pattern`` in ``folder_tokens``, if any."""
    n, m = len(folder_tokens), len(pattern)
    if m == 0 or m > n:
        return None
    best: int | None = None
    for start in range(n - m + 1):
        if tuple(folder_tokens[start : start + m]) == pattern:
            best = start + m - 1
    return best


def classify_course(folder_tokens: list[str], matchers: list[_Matcher]) -> CourseDecision:
    """Pure function: pick the course whose matcher reaches deepest into ``folder_tokens``.

    Ties (same deepest end index) go to the longer matcher, then to declaration order in the curated map.
    """
    best_matcher: _Matcher | None = None
    best_end = -1
    best_index = -1
    for index, matcher in enumerate(matchers):
        end = _last_match_end(folder_tokens, matcher.tokens)
        if end is None:
            continue
        longer_at_same_depth = (
            end == best_end and best_matcher is not None and len(matcher.tokens) > len(best_matcher.tokens)
        )
        if best_matcher is None or end > best_end or longer_at_same_depth:
            best_matcher, best_end = matcher, end
            best_index = index
        elif end == best_end and len(matcher.tokens) == len(best_matcher.tokens) and index < best_index:
            best_matcher, best_end, best_index = matcher, end, index
    if best_matcher is None:
        return CourseDecision(course_id=None, confidence=None)
    return CourseDecision(course_id=best_matcher.course_id, confidence=best_matcher.confidence)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def classify_courses(
    config: SbrConfig,
    db: RegistryDB,
    *,
    course_map_path: Path | None = None,
    owner: str = "system:course-classifier",
    clock: Callable[[], datetime] = _utcnow,
) -> CoursesRunResult:
    """Assign a curated course_id/confidence to every currently-known, knowledge-bearing blob's folder path."""
    curation_root = Path(config.roots.curation)
    map_file = course_map_path or curation_root / DEFAULT_COURSE_MAP_NAME
    matchers = build_matchers(load_course_map(map_file).records)

    blobs = {b.blob_id: b for b in db.repo(reg.BLOB).find()}
    current_by_blob: dict[str, PathObservation] = {}
    for obs in db.repo(reg.PATH_OBSERVATION).find({"state": ObservationState.PRESENT}):
        if obs.blob_id is not None and obs.blob_id not in current_by_blob and obs.blob_id in blobs:
            blob = blobs[obs.blob_id]
            if blob.knowledge_class not in _INELIGIBLE_KNOWLEDGE_CLASSES:
                current_by_blob[obs.blob_id] = obs

    classifications = db.repo(reg.BLOB_CLASSIFICATION)
    classified = 0
    unknown = 0

    provenance = ProvenanceStore(db.conn, clock=clock)
    with provenance.activity(
        kind=COURSES_STAGE,
        producer=COURSES_PRODUCER,
        producer_version=__version__,
        agent=owner,
        params={"course_map": str(map_file)},
    ) as activity:
        with transaction(db.conn):
            outputs: list[str] = []
            for blob_id, obs in current_by_blob.items():
                decision = classify_course(obs.folder_tokens, matchers)
                if decision.course_id is None:
                    unknown += 1
                    continue
                existing = classifications.find({"blob_id": blob_id})
                base = existing[0] if existing else None
                classifications.upsert(
                    BlobClassification(
                        blob_id=blob_id,
                        genre=base.genre if base is not None else None,
                        genre_confidence=base.genre_confidence if base is not None else None,
                        course_id=decision.course_id,
                        course_confidence=decision.confidence,
                        language_guess=base.language_guess if base is not None else None,
                        semester=base.semester if base is not None else None,
                        institution=base.institution if base is not None else None,
                        isbn=base.isbn if base is not None else None,
                        rules_version=base.rules_version if base is not None else GENRE_RULES_VERSION,
                        activity_id=activity.activity_id,
                    )
                )
                classified += 1
                outputs.append(blob_id)
        activity.outputs.extend(outputs)

    return CoursesRunResult(
        activity_id=activity.activity_id,
        considered=len(current_by_blob),
        classified=classified,
        unknown=unknown,
    )


__all__ = [
    "ALIAS_CONFIDENCE",
    "COURSES_PRODUCER",
    "COURSES_STAGE",
    "DEFAULT_COURSE_MAP_NAME",
    "PATTERN_CONFIDENCE",
    "CourseDecision",
    "CoursesRunResult",
    "build_matchers",
    "classify_course",
    "classify_courses",
]
