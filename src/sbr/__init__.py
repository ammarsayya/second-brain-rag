"""Second Brain RAG (``sbr``): a local-first, provenance-tracked agentic RAG over the owner's corpus.

Architecture and plan: ``docs/`` (start with ``docs/00_PROJECT_OVERVIEW.md``).
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("second-brain-rag")
except PackageNotFoundError:  # pragma: no cover - running from a source tree without installation
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
