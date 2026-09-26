"""T-P3-08 SPIKE-OCR: pure Tesseract TSV parsing."""

from __future__ import annotations

from sbr.eval.extract.ocr import mean_word_confidence, parse_tesseract_tsv

# A real (trimmed) sample of `tesseract <img> stdout -l deu tsv` output, captured against a real corpus
# scanned page - structural rows (level 1-4) carry conf=-1 and no text; only level-5 word rows have both.
REAL_TSV_SAMPLE = (
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    "1\t1\t0\t0\t0\t0\t0\t0\t1654\t2338\t-1\t\n"
    "2\t1\t1\t0\t0\t0\t1617\t10\t24\t2284\t-1\t\n"
    "5\t1\t1\t1\t1\t1\t1617\t10\t24\t2284\t95.000000\tHallo\n"
    "5\t1\t1\t1\t1\t2\t1700\t10\t24\t2284\t42.500000\tWelt\n"
)


def test_parse_tesseract_tsv_extracts_only_word_rows() -> None:
    words = parse_tesseract_tsv(REAL_TSV_SAMPLE)
    assert [w.text for w in words] == ["Hallo", "Welt"]
    assert words[0].confidence == 95.0
    assert words[1].confidence == 42.5


def test_parse_tesseract_tsv_skips_blank_text_rows() -> None:
    words = parse_tesseract_tsv(REAL_TSV_SAMPLE)
    assert all(w.text.strip() for w in words)


def test_mean_word_confidence() -> None:
    words = parse_tesseract_tsv(REAL_TSV_SAMPLE)
    assert mean_word_confidence(words) == (95.0 + 42.5) / 2


def test_mean_word_confidence_of_no_words_is_none() -> None:
    assert mean_word_confidence([]) is None


def test_parse_tesseract_tsv_handles_a_header_only_output() -> None:
    header_only = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    assert parse_tesseract_tsv(header_only) == []
