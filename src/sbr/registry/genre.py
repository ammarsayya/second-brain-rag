"""Genre classification v1 and exam/exercise-solution pairing (T-P2-10).

Rule-based genre from path/name tokens only — the same "metadata, not content"
discipline as classification (T-P2-04) and sensitivity (T-P2-05): this stage
never opens a source file. Genre and its confidence are stored on
:class:`~sbr.schemas.registry.BlobClassification` (already built for this by
T-P1-05, no schema change needed); a ``Lösung`` (solution) blob is additionally
paired with the exam/exercise it most likely answers via a ``solution_of``
:class:`~sbr.schemas.registry.BlobRelation` (also pre-existing).

Genre keywords (docs/03 §2's own naming-convention census — German academic
filenames): ``exam`` (Klausur/Kla/Kl), ``solution`` (Lösung/Musterlösung/
Kurzlösung/TutLos), ``exercise`` (Übung/Aufgabenblatt/Uebungsblatt), ``script``
(Skript/Sk), ``lab`` (Labor/Versuch), ``report`` (Bericht), ``thesis``
(Bachelorarbeit/Masterarbeit/Diplomarbeit), ``textbook`` (an ISBN-10/13
pattern anywhere in the path — a strong, distinct signal independent of the
keyword list). All keyword matching is whole-token (word-boundary regex over
casefolded path components), not raw substring search, so short tokens like
``kl``/``sk`` do not false-positive inside unrelated words.

Solution pairing is a lightweight, self-contained heuristic (T-P2-11's course
map does not exist yet and is not a dependency here): a ``solution``-genre
blob is paired with the closest ``exam``/``exercise``-genre blob that shares
its semester token (if any) and is folder-proximate (same folder, or an
immediate parent/child — the same distance rule as T-P2-09's twin detection),
ranked by stem overlap after stripping the genre keyword itself from both
sides.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import PureWindowsPath
from typing import Final

from sbr import __version__
from sbr.config import SbrConfig
from sbr.db import registry as reg
from sbr.db.connection import transaction
from sbr.db.registry import RegistryDB
from sbr.provenance import ProvenanceStore
from sbr.schemas import BlobClassification, PathObservation
from sbr.schemas.registry import BlobRelation, ObservationState, RelationStatus, RelationType

GENRE_PRODUCER: Final = "sbr.registry.genre"
GENRE_STAGE: Final = "genre"
GENRE_RULES_VERSION: Final = "1"

MAX_FOLDER_DISTANCE: Final = 1

# \b alone is not enough: '_' is a regex "word" character, so it creates no boundary against an adjacent
# token in this corpus's dominant "Klausur_SS2019.pdf" underscore-joined naming style. Matching runs against
# a delimiter-normalized copy (see _normalize_delimiters) where '_'/'-'/'.' are turned into spaces first, so
# \b works as intended everywhere below.

# Ordered by specificity: a path can match more than one rule (e.g. "Klausur_Loesung.pdf" contains both an
# exam and a solution token) — the FIRST matching rule below wins, so more specific/definitive genres
# (solution, thesis, report) are listed before broader ones (exam, exercise) where real filenames combine them.
_GENRE_RULES: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("thesis", re.compile(r"\b(bachelorarbeit|masterarbeit|diplomarbeit)\b", re.IGNORECASE)),
    (
        "solution",
        re.compile(r"\b(l(ö|oe)sung(en)?|musterl(ö|oe)sung(en)?|kurzl(ö|oe)sung(en)?|tutlos|lsg)\b", re.IGNORECASE),
    ),
    ("report", re.compile(r"\bbericht(e)?\b", re.IGNORECASE)),
    ("lab", re.compile(r"\b(labor|versuch(e)?)\b", re.IGNORECASE)),
    ("exam", re.compile(r"\b(klausur(en)?|kla|kl)\b", re.IGNORECASE)),
    (
        "exercise",
        re.compile(r"\b(übung(en)?|uebung(en)?|aufgabenblatt|aufgabenblätter|aufgabenblaetter)\b", re.IGNORECASE),
    ),
    ("script", re.compile(r"\b(skript(e)?|sk)\b", re.IGNORECASE)),
)
_SOLUTION_TARGET_GENRES: Final = frozenset({"exam", "exercise"})

_DELIMITER: Final = re.compile(r"[_\-.]")
_ISBN_PATTERN: Final = re.compile(r"\bisbn\b[:\s]*((?:97[89]\s?)?[\dXx](?:\s?[\dXx]){8,12})", re.IGNORECASE)
_SEMESTER_PATTERN: Final = re.compile(r"\b(ss|ws)\s?(\d{2,4})\b", re.IGNORECASE)


def _normalize_delimiters(text: str) -> str:
    """Turn '_'/'-'/'.' into spaces so \\b works as an intuitive word boundary against them."""
    return _DELIMITER.sub(" ", text)


@dataclass(frozen=True, slots=True)
class GenreDecision:
    genre: str | None
    confidence: float | None
    isbn: str | None
    semester: str | None


@dataclass(frozen=True, slots=True)
class SolutionPair:
    solution_blob: str
    target_blob: str
    confidence: float
    solution_relpath: str
    target_relpath: str


@dataclass(frozen=True, slots=True)
class GenreRunResult:
    activity_id: str
    considered: int
    classified: int
    solution_pairs_proposed: int


def _isbn_digits(candidate: str) -> str | None:
    digits = re.sub(r"[-\s]", "", candidate).upper()
    if len(digits) not in (10, 13):
        return None
    return digits


_BARE_ISBN13_STEM: Final = re.compile(r"^97[89][-\s]?\d[-\s]?\d{1,7}[-\s]?\d{1,7}[-\s]?\d$")


def extract_isbn(relpath: str) -> str | None:
    """Return a normalized ISBN-10/13 (digits + trailing X only) if the path contains one.

    Two patterns: an explicit "ISBN ..." label anywhere in the path, or — found in review on the real corpus,
    e.g. a textbook saved as "978-3-8348-9049-8.pdf" with no "ISBN" text at all — a filename stem that is
    *itself* nothing but a hyphenated 13-digit Bookland (978/979-prefixed) number. Deliberately not extended to
    bare 10-digit stems without an explicit "ISBN" label: a random 10-digit number is too easily something
    else entirely (an ID, a phone number, a date-like string).
    """
    match = _ISBN_PATTERN.search(_normalize_delimiters(relpath))
    if match is not None:
        return _isbn_digits(match.group(1))
    stem = PureWindowsPath(relpath).stem
    if _BARE_ISBN13_STEM.match(stem) is not None:
        return _isbn_digits(stem)
    return None


def extract_semester(relpath: str) -> str | None:
    """Return a normalized semester token (e.g. "ss2019", "ws0910") if the path contains one."""
    match = _SEMESTER_PATTERN.search(_normalize_delimiters(relpath))
    if match is None:
        return None
    return f"{match.group(1).lower()}{match.group(2)}"


def classify_genre(relpath: str) -> GenreDecision:
    """Pure function: decide one path's genre, confidence, ISBN and semester from its name/path alone.

    Filename-level match only — an earlier version also fell back to an ancestor-*folder*-only match at a
    lower confidence (e.g. anything under a "BachelorArbeit\\" project folder, regardless of the file's own
    name). Found in review on the real corpus's 150-file precision sample: this made a very large fraction of
    unrelated files inside that folder tree — JPEGs, .mat data, .m scripts, even a screenshot inside a "Labor"
    folder — score genre="thesis"/"lab"/"script" despite not being thesis/lab/script documents themselves.
    Living inside a folder named after a project or course doesn't make an arbitrary file "that genre"; only
    the file's own name is evidence of what kind of document it is.
    """
    isbn = extract_isbn(relpath)
    semester = extract_semester(relpath)
    if isbn is not None:
        return GenreDecision(genre="textbook", confidence=0.95, isbn=isbn, semester=semester)
    name = _normalize_delimiters(PureWindowsPath(relpath).name)
    for genre, pattern in _GENRE_RULES:
        if pattern.search(name) is not None:
            return GenreDecision(genre=genre, confidence=0.9, isbn=None, semester=semester)
    return GenreDecision(genre=None, confidence=None, isbn=None, semester=semester)


def _folder_parts(relpath: str) -> tuple[str, ...]:
    return PureWindowsPath(relpath).parts[:-1]


def _folder_distance(a: tuple[str, ...], b: tuple[str, ...]) -> int | None:
    """0 = same folder; 1 = parent/child OR siblings under a common parent.

    Siblings matter here specifically because exam/solution pairs in this corpus routinely live in adjacent
    folders that mirror each other by name (``Klausuren/`` next to ``Loesungen/``, ``Aufgaben/`` next to
    ``Loesungen/``) rather than one nested inside the other — the parent/child-only rule that works for
    T-P2-09's twin detection (PDF and its DOCX export usually share a folder) missed this real pattern
    entirely when first tested.
    """
    if a == b:
        return 0
    if len(a) == len(b) + 1 and a[:-1] == b:
        return 1
    if len(b) == len(a) + 1 and b[:-1] == a:
        return 1
    if a and b and len(a) == len(b) and a[:-1] == b[:-1]:
        return 1
    return None


def _base_stem(relpath: str) -> str:
    """The filename stem with every genre keyword removed, for solution<->target stem overlap scoring."""
    stem = _normalize_delimiters(PureWindowsPath(relpath).stem.casefold())
    for _, pattern in _GENRE_RULES:
        stem = pattern.sub("", stem)
    return re.sub(r"\s+", " ", stem).strip()


def find_solution_pairs(
    solutions: list[tuple[PathObservation, str | None]],
    targets: list[tuple[PathObservation, str | None]],
) -> list[SolutionPair]:
    """Pure function: pair each solution observation with its best-matching exam/exercise observation.

    Each input tuple is ``(observation, semester_token_or_None)``.
    """
    targets_by_folder: dict[tuple[str, ...], list[tuple[PathObservation, str | None]]] = defaultdict(list)
    for obs, semester in targets:
        targets_by_folder[_folder_parts(obs.relpath)].append((obs, semester))

    pairs: list[SolutionPair] = []
    for solution_obs, solution_semester in solutions:
        if solution_obs.blob_id is None:
            continue
        folder = _folder_parts(solution_obs.relpath)
        nearby = {folder}
        if folder:
            nearby.add(folder[:-1])  # parent
        nearby.update(f for f in targets_by_folder if len(f) == len(folder) + 1 and f[:-1] == folder)  # children
        if folder:
            nearby.update(
                f for f in targets_by_folder if len(f) == len(folder) and f != folder and f[:-1] == folder[:-1]
            )  # siblings (e.g. "Klausuren" next to "Loesungen")

        best: SolutionPair | None = None
        solution_stem = _base_stem(solution_obs.relpath)
        for target_folder in nearby:
            for target_obs, target_semester in targets_by_folder.get(target_folder, ()):
                if target_obs.blob_id is None or target_obs.blob_id == solution_obs.blob_id:
                    continue
                distance = _folder_distance(folder, target_folder)
                if distance is None:
                    continue
                if (
                    solution_semester is not None
                    and target_semester is not None
                    and solution_semester != target_semester
                ):
                    continue
                overlap = SequenceMatcher(None, solution_stem, _base_stem(target_obs.relpath)).ratio()
                confidence = round(max(0.3, overlap) * (1.0 if distance == 0 else 0.85), 4)
                if best is None or confidence > best.confidence:
                    best = SolutionPair(
                        solution_blob=solution_obs.blob_id,
                        target_blob=target_obs.blob_id,
                        confidence=confidence,
                        solution_relpath=solution_obs.relpath,
                        target_relpath=target_obs.relpath,
                    )
        if best is not None:
            pairs.append(best)
    return sorted(pairs, key=lambda p: (-p.confidence, p.solution_blob))


def _utcnow() -> datetime:
    return datetime.now(UTC)


def classify_genres(
    config: SbrConfig,
    db: RegistryDB,
    *,
    owner: str = "system:genre-classifier",
    clock: Callable[[], datetime] = _utcnow,
) -> GenreRunResult:
    """Classify genre for every currently-known blob and propose solution_of pairings."""
    current_by_blob: dict[str, PathObservation] = {}
    for obs in db.repo(reg.PATH_OBSERVATION).find({"state": ObservationState.PRESENT}):
        if obs.blob_id is not None and obs.blob_id not in current_by_blob:
            current_by_blob[obs.blob_id] = obs

    decisions: dict[str, GenreDecision] = {
        blob_id: classify_genre(obs.relpath) for blob_id, obs in current_by_blob.items()
    }

    solutions = [
        (current_by_blob[blob_id], decision.semester)
        for blob_id, decision in decisions.items()
        if decision.genre == "solution"
    ]
    targets = [
        (current_by_blob[blob_id], decision.semester)
        for blob_id, decision in decisions.items()
        if decision.genre in _SOLUTION_TARGET_GENRES
    ]
    pairs = find_solution_pairs(solutions, targets)

    classifications = db.repo(reg.BLOB_CLASSIFICATION)
    relations = db.repo(reg.BLOB_RELATION)
    classified = 0

    provenance = ProvenanceStore(db.conn, clock=clock)
    with provenance.activity(
        kind=GENRE_STAGE,
        producer=GENRE_PRODUCER,
        producer_version=__version__,
        agent=owner,
        params={"rules_version": GENRE_RULES_VERSION},
    ) as activity:
        with transaction(db.conn):
            for blob_id, decision in decisions.items():
                if decision.genre is None and decision.isbn is None and decision.semester is None:
                    continue
                classifications.upsert(
                    BlobClassification(
                        blob_id=blob_id,
                        genre=decision.genre,
                        genre_confidence=decision.confidence,
                        semester=decision.semester,
                        isbn=decision.isbn,
                        rules_version=GENRE_RULES_VERSION,
                        activity_id=activity.activity_id,
                    )
                )
                classified += 1
            for pair in pairs:
                relations.upsert(
                    BlobRelation(
                        src_blob=pair.solution_blob,
                        dst_blob=pair.target_blob,
                        type=RelationType.SOLUTION_OF,
                        confidence=pair.confidence,
                        evidence={},
                        status=RelationStatus.CANDIDATE,
                        activity_id=activity.activity_id,
                    )
                )
        activity.outputs.extend(
            dict.fromkeys(
                [blob_id for blob_id in decisions if decisions[blob_id].genre is not None]
                + [blob_id for pair in pairs for blob_id in (pair.solution_blob, pair.target_blob)]
            )
        )

    return GenreRunResult(
        activity_id=activity.activity_id,
        considered=len(current_by_blob),
        classified=classified,
        solution_pairs_proposed=len(pairs),
    )


__all__ = [
    "GENRE_PRODUCER",
    "GENRE_RULES_VERSION",
    "GENRE_STAGE",
    "MAX_FOLDER_DISTANCE",
    "GenreDecision",
    "GenreRunResult",
    "SolutionPair",
    "classify_genre",
    "classify_genres",
    "extract_isbn",
    "extract_semester",
    "find_solution_pairs",
]
