"""Extraction evaluation harness (T-P3-04, docs/20 "Evaluation Strategy").

Objective engine comparison for the P3 extraction-technology spikes (T-P3-05 onward): every candidate parser
implements :class:`~sbr.eval.extract.contracts.Extractor`, the harness (:mod:`sbr.eval.extract.harness`) runs
it against gold references built by T-P3-01/02/03, and :mod:`sbr.eval.extract.metrics` scores the result the
same way for every engine so the comparison is apples-to-apples.
"""

from __future__ import annotations
