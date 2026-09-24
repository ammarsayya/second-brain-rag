# 16 — External Research and Approval

Autonomous gap research is approved. **Permanent ingestion requires owner approval** (HC-10, ADR-028).

## 1. Workflow

```
KnowledgeGap (open)
 → PLAN      research questions, target claims, source-type priorities, budget
 → SEARCH    web search, arXiv, OpenAlex/Semantic Scholar, university course pages, standards bodies, docs sites, YouTube
 → FETCH     full documents (PDF/HTML/transcript) → QUARANTINE store (var/research/quarantine/<hash>) — snippets are never knowledge
 → EVALUATE  per source: type (peer-reviewed, textbook, course, standard, official docs, reputable site, video), authority, recency,
             relevance, independence, license note → score + rationale
 → EXTRACT   claims with exact supporting spans (quotes + locators)
 → COMPARE   against the corpus (local retrieval): agree / extend / conflict → Conflict records
 → SYNTHESIZE ResearchProposal (EXTERNAL_PENDING)
 → REVIEW    owner: approve | approve-with-edits | reject | request-more
 → INGEST    approved sources → accepted-external source root → the normal pipeline with provenance EXTERNAL_RESEARCH
             + proposal → approved research note (vault research/)
 → ARCHIVE   rejected → kept in the research log (reason), excluded from indexes
```

## 2. Source policy

- **Preferred:** primary sources (papers, standards, official documentation), textbooks, university courses (lecture notes and syllabi), high-quality videos (lectures) with transcripts.
- **Allowed with lower authority:** reputable technical sites and blogs by recognized experts.
- **Disallowed as evidence:** search snippets, AI-generated content farms, unattributed pages. Content behind paywalls is not scraped. Robots and terms are respected.
- Every claim needs ≥2 independent sources, or one primary authoritative source, to be marked `well_supported`.

## 3. ResearchProposal note (vault `inbox/research/`)

Frontmatter: `provenance_class: EXTERNAL_PENDING`, `gap: [[…]]`, `status: pending_review`, `sources: [...]`, `budget_used`.
Body: summary, claims table (claim, support, sources, confidence), conflicts with the corpus, recommended actions, open issues.
Approval can be given by editing `status: approved|rejected` in Obsidian (picked up by the watcher) or with `sbr research approve <id>`.
Both are recorded in the curation ledger with a timestamp.

## 4. Contamination guards (T-P12-06)

- Quarantined content lives only in the `pending` index, which is used by the Research workflow for dedup and comparison.
- Main indexes include only `root.kind ∈ {university, personal, external_accepted}`.
- Tests assert that a pending source never appears in `sbr ask` evidence.
- Answers may *mention* pending research only with an explicit "unapproved external" label, and only if the owner enables that option.

## 5. Stopping and budgets

Per run: max sources fetched (default 15), max LLM tokens, max wall-clock time, max search queries. The run stops early when target claims are well supported.
Budget exhaustion yields a partial proposal that lists the remaining questions.

## 6. Videos

Approved as a source category. The system fetches transcripts (official captions, or local Whisper later) and cites timestamps.
A video counts as authoritative only when the channel is an institution or a recognized expert.
