"""Render the curated taxonomy and course map as one static owner-review page.

The source YAML files are validated through the canonical curation loaders and
are never modified.  ``--prepare`` writes only the requested HTML output.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sbr.curation import CourseMapEntry, TaxonomyConcept, load_course_map, load_taxonomy

DEFAULT_TAXONOMY = Path("curation/taxonomy.yaml")
DEFAULT_COURSE_MAP = Path("curation/course_map.yaml")
DEFAULT_OUTPUT = Path("eval/gold/taxonomy/review/index.html")
DEFAULT_AMBIGUOUS_THRESHOLD = 3


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a static owner-review page for Taxonomy v0.")
    parser.add_argument("--prepare", action="store_true", required=True, help="Render the review HTML.")
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--course-map", type=Path, default=DEFAULT_COURSE_MAP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--ambiguous-threshold",
        type=int,
        default=DEFAULT_AMBIGUOUS_THRESHOLD,
        help="Flag courses mapped to more than this many domains (default: 3).",
    )
    return parser.parse_args()


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _validate_references(
    concepts: tuple[TaxonomyConcept, ...], courses: tuple[CourseMapEntry, ...]
) -> dict[str, TaxonomyConcept]:
    by_id = {concept.concept_id: concept for concept in concepts}
    if len(by_id) != len(concepts):
        raise ValueError("taxonomy contains duplicate concept_id values")
    course_ids = {course.course_id for course in courses}
    if len(course_ids) != len(courses):
        raise ValueError("course map contains duplicate course_id values")

    for concept in concepts:
        for relation in ("broader", "narrower", "related"):
            unknown = sorted(set(getattr(concept, relation)) - by_id.keys())
            if unknown:
                raise ValueError(f"{concept.concept_id}.{relation} references unknown concepts: {unknown}")
    for course in courses:
        unknown = sorted(set(course.domains) - by_id.keys())
        if unknown:
            raise ValueError(f"{course.course_id}.domains references unknown concepts: {unknown}")
    return by_id


def _top_domains(
    concept_id: str,
    concepts: dict[str, TaxonomyConcept],
    cache: dict[str, frozenset[str]],
    visiting: frozenset[str] = frozenset(),
) -> frozenset[str]:
    if concept_id in cache:
        return cache[concept_id]
    if concept_id in visiting:
        cycle = " -> ".join([*sorted(visiting), concept_id])
        raise ValueError(f"cycle in broader hierarchy: {cycle}")
    parents = concepts[concept_id].broader
    roots = (
        frozenset({concept_id})
        if not parents
        else frozenset(
            root for parent in parents for root in _top_domains(parent, concepts, cache, visiting | {concept_id})
        )
    )
    cache[concept_id] = roots
    return roots


def _concept_link(concept_id: str, concepts: dict[str, TaxonomyConcept]) -> str:
    concept = concepts[concept_id]
    return (
        f'<a href="#concept-{_escape(concept_id)}"><code>{_escape(concept_id)}</code></a>'
        f" — {_escape(concept.label_en)} / {_escape(concept.label_de)}"
    )


def _render_hierarchy_node(
    concept_id: str,
    concepts: dict[str, TaxonomyConcept],
    children: dict[str, list[str]],
    trail: frozenset[str],
) -> str:
    if concept_id in trail:
        return f'<li class="warning">Cycle stopped at <code>{_escape(concept_id)}</code></li>'
    concept = concepts[concept_id]
    parent_note = ""
    if len(concept.broader) > 1:
        parents = ", ".join(_concept_link(parent, concepts) for parent in concept.broader)
        parent_note = f'<div class="poly"><strong>Poly-hierarchy:</strong> all parents: {parents}</div>'
    descendants = "".join(
        _render_hierarchy_node(child, concepts, children, trail | {concept_id})
        for child in children.get(concept_id, [])
    )
    nested = f"<ul>{descendants}</ul>" if descendants else ""
    return f"<li>{_concept_link(concept_id, concepts)}{parent_note}{nested}</li>"


def _render_id_list(ids: Iterable[str], concepts: dict[str, TaxonomyConcept], *, empty: str) -> str:
    values = list(ids)
    if not values:
        return f'<p class="ok">{_escape(empty)}</p>'
    return "<ul>" + "".join(f"<li>{_concept_link(value, concepts)}</li>" for value in values) + "</ul>"


def _cross_disciplinary_findings(
    concepts: dict[str, TaxonomyConcept], roots: dict[str, frozenset[str]]
) -> dict[str, list[str]]:
    inbound_related: dict[str, set[str]] = defaultdict(set)
    for source in concepts.values():
        for target in source.related:
            inbound_related[target].add(source.concept_id)

    findings: dict[str, list[str]] = {}
    for concept_id, concept in concepts.items():
        reasons: list[str] = []
        source_domains = {root for source in inbound_related.get(concept_id, set()) for root in roots[source]}
        if len(source_domains) > 1:
            reasons.append("related target from multiple top-level domains: " + ", ".join(sorted(source_domains)))

        broader_crosses = len({root for parent in concept.broader for root in roots[parent]}) > 1
        related_crosses = any(roots[target] != roots[concept_id] for target in concept.related)
        if broader_crosses and related_crosses:
            reasons.append("both broader and related links cross top-level domain boundaries")
        if reasons:
            findings[concept_id] = reasons
    return findings


def render_taxonomy_review(
    taxonomy_path: Path,
    course_map_path: Path,
    output_path: Path,
    *,
    ambiguous_threshold: int = DEFAULT_AMBIGUOUS_THRESHOLD,
) -> dict[str, Any]:
    """Validate inputs, compute review findings, and write one self-contained HTML file."""
    if ambiguous_threshold < 0:
        raise ValueError("ambiguous_threshold must be non-negative")
    concepts_in_order = load_taxonomy(taxonomy_path).records
    courses = load_course_map(course_map_path).records
    concepts = _validate_references(concepts_in_order, courses)

    root_cache: dict[str, frozenset[str]] = {}
    roots = {concept_id: _top_domains(concept_id, concepts, root_cache) for concept_id in concepts}
    top_level = [concept.concept_id for concept in concepts_in_order if not concept.broader]
    children: dict[str, list[str]] = defaultdict(list)
    for concept in concepts_in_order:
        for parent in concept.broader:
            children[parent].append(concept.concept_id)

    mapped_ids = {domain for course in courses for domain in course.domains}
    unmapped_courses = [course for course in courses if not course.domains]
    unmapped_concepts = [concept.concept_id for concept in concepts_in_order if concept.concept_id not in mapped_ids]
    ambiguous_courses = [course for course in courses if len(course.domains) > ambiguous_threshold]
    cross_findings = _cross_disciplinary_findings(concepts, roots)

    hierarchy_sections: list[str] = []
    for root in top_level:
        root_children = "".join(
            _render_hierarchy_node(child, concepts, children, frozenset({root})) for child in children.get(root, [])
        )
        hierarchy_sections.append(
            f'<section class="domain"><h3>{_concept_link(root, concepts)}</h3>'
            f'<ul class="tree">{root_children}</ul></section>'
        )
    hierarchy = "".join(hierarchy_sections)
    concept_rows = "".join(
        f'<tr id="concept-{_escape(concept.concept_id)}"><td><code>{_escape(concept.concept_id)}</code></td>'
        f"<td>{_escape(concept.label_en)}</td><td>{_escape(concept.label_de)}</td>"
        f"<td>{', '.join(_escape(root) for root in sorted(roots[concept.concept_id]))}</td></tr>"
        for concept in concepts_in_order
    )
    course_rows = "".join(
        f"<tr><td><code>{_escape(course.course_id)}</code></td><td>{_escape(course.name)}</td><td>"
        + (
            "<br>".join(_concept_link(domain, concepts) for domain in course.domains)
            if course.domains
            else '<strong class="flag">No domains</strong>'
        )
        + "</td></tr>"
        for course in courses
    )
    cross_html = (
        "<ul>"
        + "".join(
            f"<li>{_concept_link(concept_id, concepts)}<ul>"
            + "".join(f"<li>{_escape(reason)}</li>" for reason in reasons)
            + "</ul></li>"
            for concept_id, reasons in cross_findings.items()
        )
        + "</ul>"
        if cross_findings
        else '<p class="ok">No cross-disciplinary concepts matched the stated criteria.</p>'
    )
    unmapped_course_html = (
        "<ul>"
        + "".join(
            f"<li><code>{_escape(course.course_id)}</code> — {_escape(course.name)}</li>" for course in unmapped_courses
        )
        + "</ul>"
        if unmapped_courses
        else '<p class="ok">No courses have zero domains.</p>'
    )
    ambiguous_html = (
        "<ul>"
        + "".join(
            f"<li><code>{_escape(course.course_id)}</code> — {_escape(course.name)} "
            f"({len(course.domains)} domains)</li>"
            for course in ambiguous_courses
        )
        + "</ul>"
        if ambiguous_courses
        else f'<p class="ok">No courses map to more than {ambiguous_threshold} domains.</p>'
    )
    owner_decision = (
        "Owner decision: APPROVE / REQUEST CHANGES (record separately, e.g. in docs/24_DECISION_LOG.md against T-P5-06)"
    )

    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Taxonomy v0 owner review</title>
<style>
:root{{--ink:#172033;--muted:#526070;--line:#d8dee8;--paper:#fff;--bg:#f5f7fa;--accent:#2156a5;--warn:#a94814}}
*{{box-sizing:border-box}} body{{font:15px/1.5 system-ui,sans-serif;color:var(--ink);background:var(--bg);margin:0}}
main{{max-width:1180px;margin:auto;padding:2rem}}
section{{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:1rem 1.25rem;margin:1rem 0}}
h1,h2,h3{{line-height:1.2}} a{{color:var(--accent)}} code{{overflow-wrap:anywhere}}
.summary{{display:flex;gap:.6rem;flex-wrap:wrap}}
.summary span{{background:#e9f0fb;border-radius:999px;padding:.3rem .7rem}}
.domain{{margin:.7rem 0}} .tree ul{{border-left:2px solid var(--line)}}
.poly{{color:var(--warn);margin:.25rem 0 .5rem 0}}
table{{border-collapse:collapse;width:100%}}
th,td{{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:.55rem}}
th{{position:sticky;top:0;background:#eef2f7}} .table-wrap{{overflow:auto}}
.ok{{color:#246b3f}} .flag{{color:var(--warn)}} footer{{font-weight:700;margin:2rem 0}}
@media(max-width:700px){{main{{padding:1rem}} th{{position:static}}}}
</style></head><body><main>
<h1>Taxonomy v0 owner review</h1>
<p>This static page renders only identifiers, labels, and relationships present in the two curated YAML files.
It records no decision.</p>
<div class="summary">
<span>{len(concepts_in_order)} concepts</span><span>{len(courses)} courses</span>
<span>{len(top_level)} top-level domains</span><span>{len(cross_findings)} cross-disciplinary flags</span>
</div>
<h2>Hierarchy</h2>
<p>Every concept is grouped under each top-level domain reachable through <code>broader</code>.
Orange notes make multiple-parent placement explicit.</p>
{hierarchy}
<section><h2>Concept aliases</h2><div class="table-wrap"><table><thead><tr>
<th>concept_id</th><th>label_en</th><th>label_de</th><th>top-level domain(s)</th>
</tr></thead><tbody>{concept_rows}</tbody></table></div></section>
<section><h2>Course-to-domain mappings</h2><div class="table-wrap"><table><thead><tr>
<th>course_id</th><th>name</th><th>mapped concept id / labels</th>
</tr></thead><tbody>{course_rows}</tbody></table></div></section>
<section id="unmapped-ambiguous"><h2>Unmapped and ambiguous cases</h2>
<h3>Courses with zero domains</h3>{unmapped_course_html}
<h3>Concepts with zero directly mapped courses</h3>
{_render_id_list(unmapped_concepts, concepts, empty="Every concept has at least one directly mapped course.")}
<h3>Courses mapped to more than {ambiguous_threshold} domains</h3>{ambiguous_html}</section>
<section id="cross-disciplinary"><h2>Cross-disciplinary concepts</h2>
<p>Flagged when a concept is the target of <code>related</code> links from more than one top-level domain,
or when it has both multi-domain <code>broader</code> links and cross-domain <code>related</code> links.</p>
{cross_html}</section>
<footer>{owner_decision}</footer>
</main></body></html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return {
        "ambiguous_courses": [course.course_id for course in ambiguous_courses],
        "ambiguous_threshold": ambiguous_threshold,
        "concept_count": len(concepts_in_order),
        "course_count": len(courses),
        "cross_disciplinary_concepts": list(cross_findings),
        "output": str(output_path),
        "top_level_domain_count": len(top_level),
        "unmapped_concepts": unmapped_concepts,
        "unmapped_courses": [course.course_id for course in unmapped_courses],
    }


def main() -> int:
    args = _arguments()
    result = render_taxonomy_review(
        args.taxonomy,
        args.course_map,
        args.output,
        ambiguous_threshold=args.ambiguous_threshold,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
