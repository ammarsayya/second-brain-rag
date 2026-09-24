"""Independent spot-check validator for T-P2-02 BLAKE3 blob identities.

JSON is written to stdout for automation and a one-line summary to stderr.  A
fixed seed makes sampling reproducible.  The verification pass uses plain
read-only file I/O and the ``blake3`` package directly, never
``sbr.ids.hash_stream``, so it is independent from the production hash path.

With ``--config`` the script samples already-hashed observations from the
configured registry.  With ``--corpus`` it builds a temporary registry, runs S1,
then hashes only the sampled observations through the production primitives
before independently validating them; no state is written inside the corpus.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
import time
from pathlib import Path
from typing import BinaryIO

import blake3

from sbr.config import SbrConfig, config_from_mapping, load_config, resolve_config_path
from sbr.db import registry as reg
from sbr.db.registry import RegistryDB
from sbr.ids import hash_stream
from sbr.registry.scan import scan_root
from sbr.schemas.registry import ObservationState, PathObservation
from sbr.sourcefs import SourceFS, split_relpath

DEFAULT_COUNT = 50
DEFAULT_SEED = 20_260_924
CHUNK_SIZE = 1024 * 1024


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spot-check stored BLAKE3 ids through an independent read path.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--corpus",
        type=Path,
        help="Corpus directory; S1 and a bounded S2 sample use a temporary registry.",
    )
    target.add_argument("--config", type=Path, help="SBR config whose existing registry contains hashed rows.")
    parser.add_argument("--root", help="Configured root id (required when --config has multiple roots).")
    parser.add_argument("-n", "--count", type=int, default=DEFAULT_COUNT, help="Maximum hashes to check.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Deterministic random-sample seed.")
    return parser.parse_args()


def _configured_target(args: argparse.Namespace, temp: Path) -> tuple[SbrConfig, str, Path, bool]:
    if args.corpus is not None:
        corpus = Path(os.path.abspath(args.corpus))
        safety_path = resolve_config_path()
        if not safety_path.is_file():
            safety_path = Path(__file__).resolve().parents[1] / "config" / "sbr.example.toml"
        safety_config = load_config(safety_path)
        config = config_from_mapping(
            {
                "roots": {
                    "sources": [{"id": "validation", "path": str(corpus)}],
                    "var": str(temp / "var"),
                    "curation": str(temp / "curation"),
                    "protected": safety_config.roots.protected,
                }
            },
            origin="validate_hash --corpus",
        )
        return config, "validation", corpus, True

    config = load_config(args.config)
    if args.root is None and len(config.roots.sources) != 1:
        raise ValueError("--root is required when the configuration has multiple source roots")
    root_id = args.root or config.roots.sources[0].id
    return config, root_id, Path(config.source_root(root_id).path), False


def _read_chunks(stream: BinaryIO) -> str:
    hasher = blake3.blake3()
    while chunk := stream.read(CHUNK_SIZE):
        hasher.update(chunk)
    return "b3:" + hasher.hexdigest()


def _independent_blob_id(root: Path, observation: PathObservation) -> str:
    path = root.joinpath(*split_relpath(observation.relpath))
    with path.open("rb") as stream:
        return _read_chunks(stream)


def _production_blob_id(source_fs: SourceFS, observation: PathObservation) -> str:
    with source_fs.open_binary(observation.root_id, observation.relpath) as stream:
        return hash_stream(stream).blob_id


def _sample(rows: list[PathObservation], count: int, seed: int) -> list[PathObservation]:
    ordered = sorted(rows, key=lambda row: row.obs_id)
    return random.Random(seed).sample(ordered, min(count, len(ordered)))


def _validate(args: argparse.Namespace, temp: Path) -> dict[str, object]:
    if args.count < 1:
        raise ValueError("--count must be at least 1")
    config, root_id, corpus, bootstrap = _configured_target(args, temp)
    if not corpus.is_dir():
        raise NotADirectoryError(str(corpus))

    with RegistryDB.open(config) as db:
        db.migrate()
        if bootstrap:
            scan_root(config, db, root_id)
        candidates = [
            row
            for row in db.repo(reg.PATH_OBSERVATION).find({"root_id": root_id})
            if row.state is ObservationState.PRESENT and (bootstrap or row.blob_id is not None)
        ]
        selected = _sample(candidates, args.count, args.seed)
        if bootstrap:
            source_fs = SourceFS(config)
            selected = [
                observation.model_copy(update={"blob_id": _production_blob_id(source_fs, observation)})
                for observation in selected
            ]

        mismatches: list[dict[str, object]] = []
        matched = 0
        for observation in selected:
            try:
                independent = _independent_blob_id(corpus, observation)
            except OSError as exc:
                mismatches.append({"obs_id": observation.obs_id, "error": type(exc).__name__})
                continue
            if independent != observation.blob_id:
                mismatches.append(
                    {
                        "obs_id": observation.obs_id,
                        "stored_blob_id": observation.blob_id,
                        "independent_blob_id": independent,
                    }
                )
            else:
                matched += 1

    ok = bool(selected) and not mismatches
    return {
        "ok": ok,
        "exit_status": 0 if ok else 1,
        "root_id": root_id,
        "requested": args.count,
        "available": len(candidates),
        "sampled": len(selected),
        "matched": matched,
        "mismatches": mismatches,
        "seed": args.seed,
        "temporary_registry": bootstrap,
    }


def main() -> int:
    args = _arguments()
    started = time.perf_counter()
    result: dict[str, object]
    try:
        with tempfile.TemporaryDirectory(prefix="sbr-hash-validation-") as raw_temp:
            result = _validate(args, Path(raw_temp))
    except BaseException as exc:
        error = "KeyboardInterrupt" if isinstance(exc, KeyboardInterrupt) else type(exc).__name__
        result = {"ok": False, "exit_status": 1, "error": error}

    result["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print(
        "hash validation: "
        + ("PASS" if result["ok"] else "FAIL")
        + f"; matched={result.get('matched', 0)}/{result.get('sampled', 0)}"
        + f" seed={result.get('seed', '?')} elapsed={result['elapsed_seconds']}s",
        file=sys.stderr,
    )
    return int(result["exit_status"])


if __name__ == "__main__":
    raise SystemExit(main())
