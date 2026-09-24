"""T-P1-04: hashing reference vectors, bounded-memory streaming, ULIDs and anchor fingerprints."""

from __future__ import annotations

import io
import tracemalloc

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from sbr.ids import (
    UlidGenerator,
    anchor_fingerprint,
    blob_id_from_digest,
    decode_ulid,
    hamming64,
    hash_bytes,
    hash_stream,
    is_blob_id,
    new_id,
    parse_id,
    xxh3_prefilter,
)

# Official BLAKE3 test vectors (input = bytes(i % 251 for i in range(n)); default 32-byte output).
BLAKE3_VECTORS = {
    0: "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262",  # pragma: allowlist secret
    1: "2d3adedff11b61f14c886e35afa036736dcd87a74d27b5c1510225d0f592e213",  # pragma: allowlist secret
}


@pytest.mark.parametrize(("n", "expected"), BLAKE3_VECTORS.items())
def test_blake3_reference_vectors(n: int, expected: str) -> None:
    data = bytes(i % 251 for i in range(n))
    assert hash_bytes(data) == "b3:" + expected
    assert hash_stream(io.BytesIO(data)).blob_id == "b3:" + expected


@settings(max_examples=60, deadline=None)
@given(data=st.binary(max_size=20_000), chunk=st.integers(min_value=1, max_value=5000))
def test_stream_equals_oneshot_for_any_chunking(data: bytes, chunk: int) -> None:
    got = hash_stream(io.BytesIO(data), chunk_size=chunk, with_xxh3=True)
    assert got.blob_id == hash_bytes(data)
    assert got.size == len(data)
    assert got.xxh3_128 == xxh3_prefilter(data)


def test_stream_without_readinto() -> None:
    class ReadOnly:
        def __init__(self, data: bytes) -> None:
            self._b = io.BytesIO(data)

        def read(self, n: int = -1) -> bytes:
            return self._b.read(n)

    data = b"abc" * 1000
    assert hash_stream(ReadOnly(data), chunk_size=7).blob_id == hash_bytes(data)  # type: ignore[arg-type]


class _SyntheticStream(io.RawIOBase):
    """Yields ``total`` pseudo-content bytes without holding them in memory or on disk."""

    def __init__(self, total: int) -> None:
        self._left = total
        self._block = bytes(range(256)) * 4096  # 1 MiB pattern

    def readable(self) -> bool:
        return True

    def readinto(self, b: memoryview) -> int:  # type: ignore[override]
        n = min(len(b), self._left, len(self._block))
        b[:n] = self._block[:n]
        self._left -= n
        return n


@pytest.mark.slow
def test_two_gigabyte_stream_is_memory_bounded() -> None:
    total = 2 * 1024**3
    tracemalloc.start()
    try:
        result = hash_stream(_SyntheticStream(total))  # type: ignore[arg-type]
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert result.size == total
    assert is_blob_id(result.blob_id)
    assert peak < 8 * 1024 * 1024, f"peak Python allocation {peak} bytes"


def test_blob_id_validation() -> None:
    assert is_blob_id("b3:" + "0" * 64)
    assert not is_blob_id("b3:" + "0" * 63)
    assert not is_blob_id("x3:" + "0" * 64)
    assert blob_id_from_digest("A" * 64) == "b3:" + "a" * 64
    with pytest.raises(ValueError, match="BLAKE3"):
        blob_id_from_digest("zz")
    with pytest.raises(ValueError, match="positive"):
        hash_stream(io.BytesIO(b""), chunk_size=0)


def test_ulids_sortable_and_monotonic() -> None:
    clock = iter([1000, 1000, 1000, 999, 2000])  # includes a backwards clock step
    gen = UlidGenerator(clock_ms=lambda: next(clock), entropy=lambda n: b"\x00" * n)
    ids = [gen.new() for _ in range(5)]
    assert ids == sorted(ids)
    assert len(set(ids)) == 5
    assert decode_ulid(ids[0]) == (1000, 0)
    assert decode_ulid(ids[1]) == (1000, 1)
    assert decode_ulid(ids[3]) == (1000, 3)  # clock went back: stays in the last millisecond
    assert decode_ulid(ids[4])[0] == 2000


def test_real_ulids_sort_by_time() -> None:
    gen = UlidGenerator()
    ids = [gen.new() for _ in range(2000)]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


def test_prefixed_ids() -> None:
    oid = new_id("act")
    prefix, ulid = parse_id(oid)
    assert prefix == "act"
    assert len(ulid) == 26
    with pytest.raises(ValueError, match="unknown id prefix"):
        new_id("bogus")
    sample = "01J9Z3Q7C6Y8R5ZC4H2N1M0K9P"  # pragma: allowlist secret (a sample ULID)
    for bad in ("act_123", "bogus_" + sample, "act-" + sample):
        with pytest.raises(ValueError):
            parse_id(bad)


def test_decode_rejects_non_canonical() -> None:
    with pytest.raises(ValueError):
        decode_ulid("8" + "0" * 25)  # exceeds 128 bits
    with pytest.raises(ValueError):
        decode_ulid("I" * 26)  # excluded Crockford letter


TEXT = (
    "Die Übertragungsfunktion eines PT1-Gliedes lautet G(s) = K / (1 + T s). Die Sprungantwort nähert sich "
    "exponentiell dem Endwert K an; die Zeitkonstante T bestimmt die Anstiegsgeschwindigkeit des Systems."
)


def test_fingerprint_ignores_layout_and_case() -> None:
    assert anchor_fingerprint(TEXT) == anchor_fingerprint(TEXT.upper().replace(" ", "\n  "))


def test_fingerprint_similarity_ordering() -> None:
    base = anchor_fingerprint(TEXT, ["G(s) = \\frac{K}{1+Ts}"])
    small_edit = anchor_fingerprint(TEXT.replace("exponentiell", "asymptotisch"), ["G(s) = \\frac{K}{1+Ts}"])
    other = anchor_fingerprint("Der Satz von Steiner verschiebt das Flächenträgheitsmoment um A a² parallel zur Achse.")
    assert hamming64(base, small_edit) < hamming64(base, other)
    assert hamming64(base, base) == 0
    assert anchor_fingerprint("") == "0" * 16
