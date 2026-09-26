"""T-P3-01: pure document-shape signal classifiers."""

from __future__ import annotations

from sbr.eval.signals import classify_producer, has_omml_equations, is_landscape_page, is_scanned_page


def test_classify_producer_latex_variants() -> None:
    for producer in ("pdfTeX-1.40.21", "LaTeX with hyperref", "MiKTeX pdfTeX", "XeTeX"):
        assert classify_producer(producer) == "latex"


def test_classify_producer_office_variants() -> None:
    assert classify_producer("Microsoft® Word 2016") == "word"
    assert classify_producer("Microsoft® PowerPoint® 2019") == "powerpoint"
    assert classify_producer("LibreOffice 7.4") == "libreoffice"


def test_classify_producer_missing_or_unknown() -> None:
    assert classify_producer(None) == "no_metadata"
    assert classify_producer("") == "no_metadata"
    assert classify_producer("Some Scanner Vendor Tool 3.0") == "other"


def test_is_scanned_page_thresholds() -> None:
    assert is_scanned_page("") is True
    assert is_scanned_page("   \n\t  ") is True
    assert is_scanned_page("a" * 19) is True
    assert is_scanned_page("This page has a real paragraph of extracted text on it.") is False


def test_is_landscape_page() -> None:
    assert is_landscape_page(842.0, 595.0) is True  # A4 landscape
    assert is_landscape_page(595.0, 842.0) is False  # A4 portrait
    assert is_landscape_page(500.0, 500.0) is False  # square is not landscape


def test_has_omml_equations() -> None:
    assert has_omml_equations(b"<w:p><m:oMath xmlns:m='x'><m:r>x</m:r></m:oMath></w:p>") is True
    assert has_omml_equations(b"<w:p><w:r><w:t>no math here</w:t></w:r></w:p>") is False
    assert has_omml_equations(b"") is False
    # a tag name that merely starts with oMath but isn't the real element must not false-positive
    assert has_omml_equations(b"<m:oMathParaTypo>not the real tag</m:oMathParaTypo>") is False
