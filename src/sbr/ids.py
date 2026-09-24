"""Identifier and hashing core (T-P1-04, ADR-003, docs/32 conventions).

* **Blob ids**: ``b3:`` + 64 lowercase hex characters = BLAKE3-256 of the exact bytes. This is the production content
  identity. The historical audit used xxh3-128; that is available only as an optional pre-filter (``x3:`` prefix) and
  never as an identity.
* **Object ids**: type-prefixed ULIDs (``doc_01J…``). They are lexicographically sortable by creation time, and
  monotonic within one generator.
* **Anchor fingerprints**: 64-bit SimHash over normalized tokens (docs/05 §6), compared by Hamming distance.

Hashing streams through a fixed buffer, so memory stays bounded regardless of file size.
"""

from __future__ import annotations

import os
import re
import threading
import time
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import BinaryIO, Final

import blake3
import xxhash

BLOB_PREFIX: Final = "b3:"
XXH3_PREFIX: Final = "x3:"
DEFAULT_CHUNK: Final = 1024 * 1024

_BLOB_RE: Final = re.compile(r"^b3:[0-9a-f]{64}$")

# Type prefixes from docs/32 plus registry/operational types (docs/31, docs/08).
ID_PREFIXES: Final = frozenset(
    {
        "doc", "sec", "blk", "ku", "eq", "fig", "tbl", "ann", "con", "rel", "clm", "evd", "cfl", "gap", "rp", "act",
        "run", "obs", "scan", "job", "man", "ext", "chk", "note", "ref", "sym",
    }
)  # fmt: skip

_CROCKFORD: Final = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # pragma: allowlist secret (base32 alphabet)
_CROCKFORD_INDEX: Final = {c: i for i, c in enumerate(_CROCKFORD)}
_ULID_RE: Final = re.compile(r"^[0-7][0-9A-HJKMNP-TV-Z]{25}$")
_OBJ_ID_RE: Final = re.compile(r"^([a-z]+)_([0-7][0-9A-HJKMNP-TV-Z]{25})$")


# -- content hashing -----------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ContentHash:
    """Result of hashing a byte stream."""

    blob_id: str
    size: int
    xxh3_128: str | None = None  # optional pre-filter value, "x3:<32 hex>"


def is_blob_id(value: str) -> bool:
    return bool(_BLOB_RE.match(value))


def blob_id_from_digest(digest_hex: str) -> str:
    candidate = BLOB_PREFIX + digest_hex.lower()
    if not is_blob_id(candidate):
        raise ValueError(f"not a BLAKE3-256 hex digest: {digest_hex!r}")
    return candidate


def hash_bytes(data: bytes) -> str:
    """BLAKE3-256 blob id of an in-memory byte string."""
    return BLOB_PREFIX + blake3.blake3(data).hexdigest()


def hash_stream(
    stream: BinaryIO,
    *,
    chunk_size: int = DEFAULT_CHUNK,
    with_xxh3: bool = False,
    progress: Callable[[int], None] | None = None,
) -> ContentHash:
    """Stream ``stream`` to EOF through one reusable buffer and return its content hash.

    Memory use is ``chunk_size`` plus hasher state, independent of the stream length.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    hasher = blake3.blake3()
    pre = xxhash.xxh3_128() if with_xxh3 else None
    buf = bytearray(chunk_size)
    view = memoryview(buf)
    total = 0
    readinto = getattr(stream, "readinto", None)
    while True:
        if readinto is not None:
            n = readinto(view)
            if not n:
                break
            piece = view[:n]
        else:
            data = stream.read(chunk_size)
            if not data:
                break
            n = len(data)
            piece = memoryview(data)
        hasher.update(piece)
        if pre is not None:
            pre.update(piece)
        total += n
        if progress is not None:
            progress(total)
    return ContentHash(
        blob_id=BLOB_PREFIX + hasher.hexdigest(),
        size=total,
        xxh3_128=(XXH3_PREFIX + pre.hexdigest()) if pre is not None else None,
    )


def xxh3_prefilter(data: bytes) -> str:
    """Fast non-cryptographic pre-filter value. Never use it as an identity (ADR-003)."""
    return XXH3_PREFIX + xxhash.xxh3_128_hexdigest(data)


# -- ULIDs ---------------------------------------------------------------------------------------------------------


def _encode_ulid(value: int) -> str:
    chars = []
    for _ in range(26):
        chars.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def decode_ulid(ulid: str) -> tuple[int, int]:
    """Return ``(timestamp_ms, randomness)`` of a canonical ULID string."""
    if not _ULID_RE.match(ulid):
        raise ValueError(f"not a canonical ULID: {ulid!r}")
    value = 0
    for c in ulid:
        value = (value << 5) | _CROCKFORD_INDEX[c]
    return value >> 80, value & ((1 << 80) - 1)


class UlidGenerator:
    """Thread-safe, monotonic ULID generator. Clock and entropy are injectable for tests."""

    def __init__(
        self,
        clock_ms: Callable[[], int] | None = None,
        entropy: Callable[[int], bytes] | None = None,
    ) -> None:
        self._clock = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self._entropy = entropy or os.urandom
        self._lock = threading.Lock()
        self._last_ms = -1
        self._last_rand = 0

    def new(self) -> str:
        with self._lock:
            ms = self._clock()
            if ms < 0 or ms >= 1 << 48:
                raise ValueError("timestamp out of ULID range")
            if ms <= self._last_ms:
                # Same (or earlier, clock stepped back) millisecond: stay monotonic by incrementing randomness.
                ms = self._last_ms
                rand = self._last_rand + 1
                if rand >= 1 << 80:
                    raise OverflowError("ULID randomness exhausted within one millisecond")
            else:
                rand = int.from_bytes(self._entropy(10), "big")
            self._last_ms, self._last_rand = ms, rand
            return _encode_ulid((ms << 80) | rand)


_default_generator = UlidGenerator()


def new_ulid() -> str:
    return _default_generator.new()


def new_id(prefix: str, generator: UlidGenerator | None = None) -> str:
    """Return a new type-prefixed object id such as ``act_01J9Z…``."""
    if prefix not in ID_PREFIXES:
        raise ValueError(f"unknown id prefix {prefix!r}; known: {sorted(ID_PREFIXES)}")
    return f"{prefix}_{(generator or _default_generator).new()}"


def parse_id(object_id: str) -> tuple[str, str]:
    """Split ``<prefix>_<ulid>`` and validate both parts."""
    m = _OBJ_ID_RE.match(object_id)
    if not m or m.group(1) not in ID_PREFIXES:
        raise ValueError(f"not a valid sbr object id: {object_id!r}")
    return m.group(1), m.group(2)


# -- anchor fingerprints (SimHash) ---------------------------------------------------------------------------------

_TOKEN_RE: Final = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def normalize_for_fingerprint(text: str) -> list[str]:
    """NFKC, case-folded word and symbol tokens. Whitespace and layout differences do not matter."""
    return _TOKEN_RE.findall(unicodedata.normalize("NFKC", text).casefold())


def _token_hash64(token: str) -> int:
    return int.from_bytes(blake3.blake3(token.encode("utf-8")).digest(length=8), "big")


def simhash64(tokens: Iterable[str], *, shingle: int = 3) -> int:
    """64-bit SimHash over token shingles (default 3-grams; short inputs fall back to single tokens)."""
    toks = list(tokens)
    if not toks:
        return 0
    n = shingle if len(toks) >= shingle else 1
    features = [" ".join(toks[i : i + n]) for i in range(len(toks) - n + 1)]
    weights = [0] * 64
    for feat in features:
        h = _token_hash64(feat)
        for bit in range(64):
            weights[bit] += 1 if (h >> bit) & 1 else -1
    out = 0
    for bit in range(64):
        if weights[bit] > 0:
            out |= 1 << bit
    return out


def anchor_fingerprint(text: str, latex: Iterable[str] = ()) -> str:
    """Fingerprint of normalized text plus equation LaTeX (docs/05 §6), as 16 hex characters."""
    tokens = normalize_for_fingerprint(text)
    for expr in latex:
        tokens.extend(normalize_for_fingerprint(expr))
    return f"{simhash64(tokens):016x}"


def hamming64(a: int | str, b: int | str) -> int:
    ai = int(a, 16) if isinstance(a, str) else a
    bi = int(b, 16) if isinstance(b, str) else b
    return (ai ^ bi).bit_count()
