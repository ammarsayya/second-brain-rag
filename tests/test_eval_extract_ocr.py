"""T-P3-08 SPIKE-OCR: pure Tesseract TSV parsing."""

from __future__ import annotations

from sbr.eval.extract.ocr import (
    OcrWordConfidence,
    OsdResult,
    RotationVerdict,
    confident_word_count,
    mean_word_confidence,
    orientation_agreement,
    parse_tesseract_osd,
    parse_tesseract_tsv,
    pick_rotation,
    summarize_rotations,
)

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


# Real `tesseract IMG stdout --psm 0` output (Tesseract 5.5.3), captured on a synthetic German text image rotated
# by 180 degrees - the stderr warnings tesseract interleaves are included, since a caller may merge streams.
REAL_OSD_UPSIDE_DOWN = (
    "Estimating resolution as 366\n"
    "Warning. Invalid resolution 0 dpi. Using 70 instead.\n"
    "Page number: 0\n"
    "Orientation in degrees: 180\n"
    "Rotate: 180\n"
    "Orientation confidence: 17.32\n"
    "Script: Latin\n"
    "Script confidence: 28.10\n"
)
REAL_OSD_ROTATED_90 = (
    "Page number: 0\nOrientation in degrees: 270\nRotate: 90\nOrientation confidence: 12.35\n"
    "Script: Latin\nScript confidence: 22.59\n"
)
REAL_OSD_TOO_FEW_CHARACTERS = (
    "Warning. Invalid resolution 0 dpi. Using 70 instead.\nToo few characters. Skipping this page\n"
    "Error during processing.\n"
)


def test_parse_tesseract_osd_reads_rotation_and_confidences() -> None:
    result = parse_tesseract_osd(REAL_OSD_UPSIDE_DOWN)
    assert result == OsdResult(
        orientation_degrees=180, rotate=180, orientation_confidence=17.32, script="Latin", script_confidence=28.10
    )


def test_parse_tesseract_osd_keeps_rotate_distinct_from_orientation() -> None:
    result = parse_tesseract_osd(REAL_OSD_ROTATED_90)
    assert result is not None
    assert (result.orientation_degrees, result.rotate) == (270, 90)


def test_parse_tesseract_osd_fails_closed_on_too_few_characters() -> None:
    assert parse_tesseract_osd(REAL_OSD_TOO_FEW_CHARACTERS) is None
    assert parse_tesseract_osd("") is None


def test_parse_tesseract_osd_rejects_malformed_or_impossible_values() -> None:
    assert parse_tesseract_osd("Orientation in degrees: 180\nRotate: x\nOrientation confidence: 3\n") is None
    assert parse_tesseract_osd("Orientation in degrees: 45\nRotate: 45\nOrientation confidence: 3\n") is None


def test_parse_tesseract_osd_tolerates_missing_script_lines() -> None:
    result = parse_tesseract_osd("Orientation in degrees: 0\nRotate: 0\nOrientation confidence: 4.5\n")
    assert result is not None
    assert result.script is None and result.script_confidence is None


def test_summarize_rotations_separates_low_confidence_and_undetected() -> None:
    upside_down = parse_tesseract_osd(REAL_OSD_UPSIDE_DOWN)
    weak = OsdResult(0, 90, 0.4, "Latin", 1.0)
    upright = OsdResult(0, 0, 9.0, "Latin", 5.0)
    counts = summarize_rotations([upside_down, weak, upright, None], min_confidence=2.0)
    assert counts == {"0": 1, "90": 0, "180": 1, "270": 0, "low_confidence": 1, "undetected": 1}


def _words(*confidences: float) -> list[OcrWordConfidence]:
    return [OcrWordConfidence(text="w", confidence=c) for c in confidences]


def test_confident_word_count_ignores_structural_and_weak_words() -> None:
    assert confident_word_count(_words(-1, 10, 79.9, 80, 95)) == 2
    assert confident_word_count(_words(50, 60), threshold=50) == 2


def test_pick_rotation_takes_the_clear_winner() -> None:
    verdict = pick_rotation({0: 3, 90: 120, 180: 4, 270: 10})
    assert verdict == RotationVerdict(rotate=90, ambiguous=False, best_score=120, runner_up_score=10)


def test_pick_rotation_flags_a_near_tie_as_ambiguous_but_still_reports_the_leader() -> None:
    verdict = pick_rotation({0: 100, 90: 2, 180: 92, 270: 1}, margin=0.15)
    assert verdict.rotate == 0 and verdict.ambiguous


def test_pick_rotation_returns_none_when_no_rotation_reads() -> None:
    # A blank or handwriting-only page reads badly every way round: no oracle verdict, never a guessed 0.
    assert pick_rotation({0: 1, 90: 0, 180: 2, 270: 0}, min_words=5).rotate is None


def test_pick_rotation_breaks_exact_ties_toward_no_rotation() -> None:
    verdict = pick_rotation({0: 50, 90: 0, 180: 50, 270: 0})
    assert verdict.rotate == 0 and verdict.ambiguous


def test_orientation_agreement_counts_hits_misses_and_abstentions() -> None:
    table = orientation_agreement([(0, 0), (180, 0), (180, 180), (90, 90), (None, 0), (270, None)])
    assert table["compared"] == 4
    assert table["agree"] == 3
    assert table["by_osd"]["180"] == {"agree": 1, "disagree": 1}
    assert table["osd_abstained"] == 1 and table["oracle_abstained"] == 1


def test_parse_tesseract_tsv_treats_quote_marks_as_text() -> None:
    # Tesseract's TSV is not CSV-quoted. A recognised word with a quote mark (here: "Auto) must not open a quoted
    # field that swallows the following rows (real failure: "field larger than field limit").
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    rows = "".join(f"5\t1\t1\t1\t1\t{i}\t0\t0\t9\t9\t90.0\t{w}\n" for i, w in enumerate(['"Auto', "Regler", 'x"']))
    words = parse_tesseract_tsv(header + rows)
    assert [w.text for w in words] == ['"Auto', "Regler", 'x"']
