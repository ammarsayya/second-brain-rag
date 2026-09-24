"""Queue-priority hints shared by source-registry ingestion stages.

This is deliberately an extension heuristic, not file classification (T-P2-04).
Document-like extensions receive a positive hash priority so the existing
priority-ordered job queue leases them before media and other files.
"""

from __future__ import annotations

from typing import Final

DOCUMENT_HASH_PRIORITY: Final = 100
DEFAULT_HASH_PRIORITY: Final = 0
DOCUMENT_EXTENSIONS: Final = frozenset(
    {
        ".doc",
        ".docx",
        ".epub",
        ".markdown",
        ".md",
        ".mobi",
        ".odp",
        ".ods",
        ".odt",
        ".pdf",
        ".ppt",
        ".pptx",
        ".rtf",
        ".tex",
        ".txt",
        ".xls",
        ".xlsx",
    }
)


def hash_priority(relpath: str) -> int:
    """Return the S2 queue priority for a source-relative path."""
    name = relpath.replace("\\", "/").rsplit("/", 1)[-1].casefold()
    dot = name.rfind(".")
    extension = name[dot:] if dot >= 0 else ""
    return DOCUMENT_HASH_PRIORITY if extension in DOCUMENT_EXTENSIONS else DEFAULT_HASH_PRIORITY


__all__ = [
    "DEFAULT_HASH_PRIORITY",
    "DOCUMENT_EXTENSIONS",
    "DOCUMENT_HASH_PRIORITY",
    "hash_priority",
]
