"""Gold-set curation and extraction evaluation (P3, docs/33 §41).

Gold-set content (crops, derived text) is never committed — ``eval/gold/`` is git-ignored, since most sources
are copyrighted lecture/textbook material used privately (docs/22 §4). Only the *code* that builds and scores
gold sets lives in this package and is version-controlled like anything else.
"""

from __future__ import annotations
