"""T-P3-04: pure extraction-quality metric functions."""

from __future__ import annotations

from sbr.eval.extract.metrics import (
    character_error_rate,
    equation_exact_match,
    equation_token_edit_distance,
    false_confidence_rate,
    figure_detection_f1,
    heading_f1,
    levenshtein,
    normalize_latex,
    reading_order_edit_distance,
    table_structure_similarity,
    word_error_rate,
)


def test_levenshtein_basic_cases() -> None:
    assert levenshtein("", "") == 0
    assert levenshtein("abc", "abc") == 0
    assert levenshtein("", "abc") == 3
    assert levenshtein("abc", "") == 3
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein(["a", "b"], ["a", "c"]) == 1


def test_character_error_rate() -> None:
    assert character_error_rate("hello", "hello") == 0.0
    assert character_error_rate("", "") == 0.0
    assert character_error_rate("x", "") == 1.0
    assert character_error_rate("", "hello") == 1.0
    assert character_error_rate("hallo", "hello") == 1 / 5


def test_word_error_rate() -> None:
    assert word_error_rate("the cat sat", "the cat sat") == 0.0
    assert word_error_rate("the dog sat", "the cat sat") == 1 / 3


def test_reading_order_edit_distance() -> None:
    assert reading_order_edit_distance(["b1", "b2", "b3"], ["b1", "b2", "b3"]) == 0
    assert reading_order_edit_distance(["b2", "b1", "b3"], ["b1", "b2", "b3"]) == 2


def test_heading_f1_perfect_and_empty() -> None:
    assert heading_f1(set(), set()) == (1.0, 1.0, 1.0)
    assert heading_f1({"b1"}, {"b1"}) == (1.0, 1.0, 1.0)
    assert heading_f1({"b1"}, set()) == (0.0, 0.0, 0.0)
    assert heading_f1(set(), {"b1"}) == (0.0, 0.0, 0.0)


def test_heading_f1_partial_overlap() -> None:
    precision, recall, f1 = heading_f1({"b1", "b2", "b3"}, {"b1", "b2", "b4"})
    assert precision == 2 / 3
    assert recall == 2 / 3
    assert round(f1, 4) == round(2 / 3, 4)


def test_normalize_latex_strips_cosmetic_differences() -> None:
    assert normalize_latex(r"x^2  +  y^2") == normalize_latex(r"x^2 + y^2")
    assert normalize_latex(r"\left(x\right)") == normalize_latex(r"(x)")


def test_equation_exact_match() -> None:
    assert equation_exact_match(r"\left(x^2\right)", r"(x^2)") is True
    assert equation_exact_match(r"x^2", r"x^3") is False


def test_equation_token_edit_distance() -> None:
    assert equation_token_edit_distance("x + y", "x + y") == 0
    assert equation_token_edit_distance("x + z", "x + y") == 1


def test_false_confidence_rate() -> None:
    # (is_correct, is_marked_verified)
    assert false_confidence_rate([]) == 0.0
    assert false_confidence_rate([(True, False), (False, False)]) == 0.0  # nothing verified
    assert false_confidence_rate([(True, True), (False, True)]) == 0.5
    assert false_confidence_rate([(True, True), (True, True)]) == 0.0


def test_figure_detection_f1_perfect_match() -> None:
    boxes = [(0.0, 0.0, 10.0, 10.0)]
    assert figure_detection_f1(boxes, boxes) == (1.0, 1.0, 1.0)


def test_figure_detection_f1_no_overlap() -> None:
    predicted = [(0.0, 0.0, 1.0, 1.0)]
    gold = [(100.0, 100.0, 200.0, 200.0)]
    assert figure_detection_f1(predicted, gold) == (0.0, 0.0, 0.0)


def test_figure_detection_f1_empty_cases() -> None:
    assert figure_detection_f1([], []) == (1.0, 1.0, 1.0)
    assert figure_detection_f1([(0.0, 0.0, 1.0, 1.0)], []) == (0.0, 0.0, 0.0)
    assert figure_detection_f1([], [(0.0, 0.0, 1.0, 1.0)]) == (0.0, 0.0, 0.0)


def test_table_structure_similarity_identical_table() -> None:
    rows = (("a", "b"), ("c", "d"))
    assert table_structure_similarity(rows, rows) == 1.0


def test_table_structure_similarity_wrong_shape_scores_low() -> None:
    predicted = (("a", "b", "c"),)
    gold = (("a", "b"), ("c", "d"))
    score = table_structure_similarity(predicted, gold)
    assert score < 1.0


def test_table_structure_similarity_empty_cases() -> None:
    assert table_structure_similarity((), ()) == 1.0
    assert table_structure_similarity((("a",),), ()) == 0.0
    assert table_structure_similarity((), (("a",),)) == 0.0
