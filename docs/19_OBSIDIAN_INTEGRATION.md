# 19 — Obsidian Integration

Obsidian is the **human interface** to the knowledge (ADR-014). The backend never depends on Obsidian running.
All vault I/O goes through the **VaultWriter** (T-P4-13). Reading user notes goes through the vault scanner (T-P10-02).

## 1. Conventions

- Wikilinks to concept notes: `[[State-Space Representation]]`. Concept notes have `aliases: [Zustandsraumdarstellung, Zustandsraummodell]`
  so German and English links both resolve.
- Every system-written note has frontmatter: `sbr_id`, `provenance_class`, `generated_by`, `generated_at`, `content_hash`, `sources`/`citations`,
  and `status` for AI notes (`current|stale|superseded`).
- Block anchors: `^pN` (pages), `^sec-…`, `^eq-…`, `^fig-…` for deep links from citations.
- Callouts mark AI content (`> [!ai]`), uncertainty (`> [!warning]`) and model-knowledge statements (`> [!model]`).
- Optional Obsidian features (Dataview or Bases views for review queues) are enhancements only (Q-I08).

## 2. Ownership rules (the heart of HC-07/HC-08)

| Folder | Owner | System may create | System may update | System may delete |
|---|---|---|---|---|
| `notes/` | USER | ✗ | ✗ | ✗ |
| `sources/` | system (SOURCE_DERIVED) | ✓ | ✓ if unmodified since last write | ✗ (orphans are moved to `_system/orphaned/` with a note) |
| `concepts/`, `ai/`, `maps/` | system (AI_GENERATED) | ✓ | ✓ if unmodified since last write; otherwise fork | ✗ (superseded notes are kept, marked) |
| `research/` | system after approval | ✓ (on approval) | append-only corrections | ✗ |
| `inbox/` | system (proposals, review queues) | ✓ | ✓ | ✓ (after resolution, archived) |

**Unmodified check:** before updating file F, the VaultWriter recomputes the body hash and compares it with `content_hash` in F's frontmatter
and in the registry. If they match, it writes (atomic temp + rename), commits to git and records the Activity. If they don't match, **the owner edited it**,
and the VaultWriter:
1. never touches F;
2. changes F's classification in the registry to `USER_MODIFIED_GENERATED` (treated as USER_AUTHORED from then on);
3. writes the new generated version to `F.sbr-update.md` (or the `inbox/review/` queue) and notifies the owner via the review queue;
4. keeps linking both.

Files anywhere without `sbr_id` frontmatter are **USER_AUTHORED** by definition.

## 3. User-authored notes as knowledge (T-P10-02)

The vault scanner detects new or changed user notes (hash), parses frontmatter, links and headings, segments them into KUs (provenance USER_AUTHORED)
and indexes them. User notes can cite sources (`[[source note#^p22]]`). These links become graph edges with `status=curated`.
Wikilinks to concepts in user notes are strong curation signals.

## 4. AI notes and history (HC-19)

AI notes are regenerated when inputs change (staleness via input fingerprints, 05 §4). Each regeneration is a git commit in the vault,
so the history is visible in git and the Obsidian Git plugin (optional). Notes also carry a `version` counter and a short changelog section.
Old claims that disappear are listed in the changelog, not silently dropped.

## 5. Living Maps (FR-22)

`maps/<Domain>.md`, e.g. `maps/Control Engineering.md`. Required sections, each regenerated from data:
1. What knowledge exists (holdings summary, canonical sources by genre)
2. Major concepts (links) and their coverage
3. Key equations (links to equation anchors)
4. Relationships and connected disciplines (from the graph, validated edges)
5. Knowledge strength (coverage table)
6. Known gaps (from 15) and open research proposals
7. Unresolved questions and conflicts
8. `## Owner notes` (a USER section: the VaultWriter preserves anything between the `%% user-section %%` markers verbatim)

## 6. Relationship to the owner's existing Brain

The owner's Brain vault (`D:\AgenticAI\My-Knowledge\brain`) is governed separately and must not receive tens of thousands of corpus notes.
**Proposed (ADR-037):** the MBI vault is separate. The Brain holds only the project registry record and, later, distilled cross-project knowledge,
following Brain governance. Open question Q-B02 confirms the location and relationship.
