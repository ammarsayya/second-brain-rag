# 12 — Taxonomy and Knowledge Graph

## 1. Taxonomy ≠ folders ≠ graph (HC-14, HC-15)

| Structure | Purpose | Shape | Authority |
|---|---|---|---|
| **Folders in `D:\MBI-BRAIN`** | Owner's storage history | Tree (messy, cross-filed) | Kept as PathObservation metadata; mapped via the curation table |
| **Taxonomy** | Navigating knowledge by domain and topic | **Poly-hierarchy** (SKOS: broader, narrower, related), bilingual | Curation ledger `curation/taxonomy.yaml` (human-editable; AI proposes) |
| **Knowledge graph** | Meaning and relations among concepts, equations, documents and domains | Typed multigraph with evidence | Derived (var) + curated edges in the ledger |
| **Vault folders** | Human browsing in Obsidian | Tree by provenance class and domain | Layout convention (19) |

## 2. Taxonomy v0 (T-P5-06)

Seeds: `MBI-WS2019-Modulhandbuch.pdf` and `curriculum_mbi_ws2019.pdf` (module list, contents, prerequisites), the owner's folder names
via the abbreviation map (T-P2-11), and the curriculum areas in the mission. Example:

```
Engineering
 ├─ Control Engineering (Regelungstechnik)
 │   ├─ Modelling of Linear Systems ─ Transfer Functions ─ Frequency Response (Bode, Nyquist)
 │   ├─ State-Space Systems ─ Controllability ─ Observability ─ State Feedback ─ Observers
 │   └─ Controller Design (PID, root locus, …)
 ├─ Robotics ─ Kinematics (DH) ─ Dynamics ─ Robot Control ─ Motion Planning ─ Industrial Robotics
 ├─ Mechanics ─ Statics ─ Strength of Materials ─ Kinematics ─ Kinetics ─ Machine Dynamics
 ├─ Modelling & Simulation ─ FEM ─ Dynamic Simulation ─ Modelling of Technical Systems ─ CFD
 └─ Measurement & Automation ─ Measurement Eng. ─ Control (Steuerungstechnik) ─ PLC ─ Bus Systems ─ Process Control ─ Image Processing
Mathematics ─ Analysis ─ Linear Algebra ─ ODE/PDE ─ Numerical Mathematics ─ Optimization
Natural Sciences ─ Physics ─ Electrical Engineering ─ Materials Science
Computer Science ─ Fundamentals ─ Algorithms & DS ─ OOP ─ Software Engineering ─ OS ─ Systems Programming ─ Databases ─ Networks ─ IT Security
Business ─ Betriebslehre ─ Management
```
"State-Space Systems" can sit under Control Engineering *and* Mathematics › Linear Algebra › Applications (poly-hierarchy).

## 3. Graph schema (T-P8-01)

**Node types:** Concept, Equation, KU, Document, Course, Domain/Topic, Figure, Person (source-only), ExternalSource, UserNote, AINote, Gap.

**Edge types (initial):**

| Edge | Between | Produced by |
|---|---|---|
| `part_of` / `contains` | Section tree, Document↔KU | Deterministic (structure) |
| `in_course`, `in_domain` | Document/KU/Concept → Course/Domain | Rules + classification |
| `duplicate_of`, `version_of`, `contains_text_of`, `twin_of`, `annotated_variant_of` | Blob/Document | Deterministic (dedup) |
| `solution_of` | Solution doc → exam/exercise | Rules (names, same semester) + confirmation |
| `cites` | Document → Document/Reference | Reference extraction + matching |
| `mentions`, `defines` | KU → Concept | NER/term extraction + LLM with span evidence |
| `uses_equation`, `defines_symbol` | KU/Concept → Equation; Equation → SymbolDefinition | Math linking |
| `prerequisite_of` | Concept → Concept | LLM with evidence + taxonomy + module handbook prerequisites |
| `generalizes` / `special_case_of` | Concept ↔ Concept | LLM with evidence |
| `applies_to` | Concept/Method → Domain/Concept (cross-domain) | LLM with evidence |
| `equivalent_to` | Equation ↔ Equation, Concept ↔ Concept (DE/EN synonyms) | Normalization + validation |
| `contradicts` | Claim ↔ Claim | Conflict analysis |
| `depicts` / `visualizes` | Figure → Concept/Equation | Caption + reference text |

**Every non-structural edge** carries `evidence[]` (span locators mentioning both ends), `confidence`, `status`
(`extracted` → `validated` → `curated` | `rejected`), `producer` (activity). **Hallucination guard:** an LLM-proposed edge without
a verifiable evidence span is stored as `status=inferred` and **excluded from retrieval expansion** by default.

## 4. Storage (ADR-020, PROPOSED)

Canonical storage: `nodes` and `edges` tables in `knowledge.sqlite` (property graph in relational form, JSON properties).
Analytics and traversal: load into **NetworkX or igraph** in memory. The expected scale is ~20–80k concepts and ~0.5–2M edges, which fits easily in 64 GB.
Personalized PageRank, community detection and shortest paths are cheap. **No graph DB server.**
Escape hatch: if multi-hop Cypher queries become a real need, add **LadybugDB** (embedded, the Kuzu successor; Kuzu was archived after the Oct 2025 acquisition)
as a rebuildable projection. Neo4j (server, JVM) and FalkorDB (Redis) are rejected for now as operational overhead for a single-user local system.

## 5. GraphRAG approaches evaluated

| Approach | Verdict |
|---|---|
| **Microsoft GraphRAG** (LLM entity/relation extraction over all chunks + community summaries) | **Rejected as-is (ADR-022).** Indexing cost is LLM calls over every chunk (~10⁶ at our scale), it is noise-prone for German technical text, and community summaries go stale. Its useful idea (hierarchical summaries) is covered by Maps (19) on the curated graph |
| **LightRAG** (dual-level keys, incremental graph) | Candidate idea for graph-keyed retrieval; SPIKE-GRAPH compares the approach, not the library |
| **HippoRAG 2** (Personalized PageRank over a concept graph seeded by query entities) | **Most promising for cross-domain multi-hop** ("robot stabilization ↔ state feedback ↔ Lyapunov"). Tested in SPIKE-GRAPH |
| **Graphify** (owner-mentioned) | See §6 |

## 6. Graphify assessment (ADR-021, PROPOSED → SPIKE-GRAPHIFY)

Graphify (`graphifyy`, installed locally as a skill) builds a NetworkX graph from a folder. It uses AST extraction for code
and host-agent or Gemini semantic extraction for docs, papers and images, with EXTRACTED/INFERRED/AMBIGUOUS labels, Leiden communities,
an incremental cache, and exports to HTML, Obsidian, GraphML, Neo4j and MCP.

| Requirement | Graphify fit |
|---|---|
| Page/bbox-level provenance | ✗ File-level extraction by an LLM reading whole files |
| Equations as first-class LaTeX | ✗ Not modelled |
| Scale (8.6k–13.5k PDFs, 330k+ pages) | ✗ Extraction via parallel agent subagents on 20–25 files each would mean thousands of LLM batches; cost-prohibitive and uncontrolled |
| Provenance classes, approval gates | ✗ |
| Confidence labels | ✓ (EXTRACTED/INFERRED/AMBIGUOUS is a good pattern and is adopted in our edge `status`) |
| Community detection, visualization, Obsidian export, MCP | ✓ Useful for **exploration** |
| Code graphs (thesis MATLAB, Java courses) | ✓ Plausibly useful for the code track (P13) |

**Proposed:** not the core graph. Candidate uses: (a) exploration and visualization over *normalized* Markdown of one domain;
(b) code-track graphs. SPIKE-GRAPHIFY runs it on the normalized Regelungstechnik subset and compares edge precision and usefulness with our graph.

## 7. Cross-domain relations (the defining value)

The graph must make links like these discoverable:
`Robot Dynamics —uses→ Lagrange Equations (Dynamik) —special_case_of→ Principle of Virtual Work`,
`Robot Stabilization (thesis) —applies_to→ State Feedback (Regelungstechnik) —requires→ Controllability (Linear Algebra)`,
`FEM —uses→ Numerical Integration (NumMat)`.
Cross-domain edges get extra scrutiny (evidence from both domains, or explicit statements).

## 8. Quality gates (T-P8-06)

Before graph expansion is enabled in retrieval, a stratified sample of 200 edges is reviewed by an LLM judge plus owner spot checks.
Target precision ≥ 0.85 for `validated` edges (target to be confirmed in P8). Rejected patterns feed prompt and rule fixes. Metrics are tracked per edge type.
