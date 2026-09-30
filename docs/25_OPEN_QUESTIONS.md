# 25 — Open Questions

Answers must be recorded here (with date), and propagated to the decision log and execution state.
**No answer has been invented to make the plan look complete.**

## BLOCKING (each blocks specific tasks, listed in the last column)

| ID | Question | Why it matters | Blocks |
|---|---|---|---|
| Q-B01 | **Is the migration into `D:\MBI-BRAIN` finished? When is the corpus "frozen enough"?** It grew from 39k files / 371 GB to 73k / 561 GB during the audit. **Owner reported (2026-09-24): reorganization finished. Recommended resolution: CLOSE**. Evidence: t2/t2b/t2c inventories identical over 45 min; t1→t2 0 removals (docs/37 §24). **RESOLVED 2026-09-24: CLOSED.** The owner's implementation authorization of 2026-09-24 delegated closure if the post-quarantine baseline is demonstrably stable. Evidence: t2 stable 45 min; the only t2→t3 change is the 2,033 intended quarantine moves with zero unexpected additions or omissions (docs/38, `audit/phase0/t3/t2_to_t3_comparison.json`). **t3 (83,880 files, 558,752,407,625 bytes) is the implementation-source baseline**; t2 stays the historical pre-quarantine record. | Corpus statistics, wave sizing and compute planning are based on a moving snapshot | T-P2-12 (audit refresh), T-P13-01 (full ingestion). *Not* P1 or most of P2 (the incremental design tolerates change) |
| Q-B02 | **Where should the knowledge vault live, and how does it relate to the existing Brain vault?** **ANSWERED 2026-09-27** (owner's explicit direction): `D:\AgenticAI\second-brain-rag\vault`, as its own independent git repository (own `.git`, gitignored from the code repo's own history — see ADR-037), never committed into `second-brain-rag`. The Brain gets only the registry record (PRJ-0030), per the already-proposed ADR-037, now ACCEPTED | Authoritative user and AI knowledge must not sit in rebuildable `var/`; Brain governance limits | T-P4-13 (VaultWriter), T-P10-01 |
| Q-B03 | **Compute and privacy policy:** may course material and/or textbooks be sent to cloud OCR or LLM APIs? Is renting a GPU acceptable? Monthly budget ceiling? | Decides whether full-fidelity math and figure extraction takes weeks (local CPU) or days (remote), and which engines are eligible | T-P3-09 decision, T-P3-11, T-P13-01 |
| Q-B04 | **Which "OpenCode models" and how are they accessed?** (provider accounts and API keys, OpenCode Zen, GitHub Copilot, other subscriptions; can they be called programmatically outside the TUI?) | The model gateway needs concrete endpoints | T-P7-02, T-P7-01 |
| Q-B05 | **Approval of this plan** (architecture, phases, waves, first task) | Mission rule: plan approval precedes implementation | T-P1-01 and all implementation. **ANSWERED 2026-09-24: approved** (owner's explicit implementation authorization, conditional on a safe quarantine, verified; T-P0-08 DONE). The approval does not answer Q-B02–Q-B04 |

## IMPORTANT

| ID | Question | Default until answered |
|---|---|---|
| Q-I01 | Are lecture videos (~165 GB unique at t0, more at t1) in scope? Transcription wanted? | Deferred (ADR-030); registered only |
| Q-I02 | Language of generated notes and concept labels (German source language; English labels; bilingual?) | Content in the source language; concept notes bilingual (EN title + DE alias) |
| Q-I03 | Are handwritten annotations valuable enough to OCR (handwriting)? | Detect and preserve as regions; no handwriting OCR |
| Q-I04 | Third-party personal data (grade lists, other students' names, a third party's certificate found at t2): exclude entirely or keep locally searchable? | Metadata only; not processed |
| Q-I05 | Textbooks (~80% of pages): full-depth processing over time, or index-level plus JIT only? | Index-level plus JIT plus background batches by domain priority |
| Q-I06 | How many hours can the owner invest in gold-set verification (P3: ~6–12 h; P6/P7: ~3–5 h)? | Plan assumes ~10 h in P3 |
| Q-I07 | Code material (7k Java files at t1, MATLAB, C): in scope? Which parts? | Thesis MATLAB in P13 code track; the rest registered only |
| Q-I08 | Obsidian specifics: existing vault or new? Plugins acceptable (Dataview, Bases, Obsidian Git)? | New vault; plugin-free core; optional plugins |
| Q-I09 | Backup targets: private git remote for the vault and ledger? External disk? Back up `var/artifacts`? | Local git + owner-chosen external disk; artifact backup recommended after W1/W2 |
| Q-I10 | Should the system produce **cleanup suggestions** for `D:\MBI-BRAIN` (mirrored folders, duplicates) for the owner to act on manually? | Yes, report only (T-P2-07) |
| Q-I11 | Priority domains for W1 beyond the defaults (control, dynamics, robotics, modelling, FEM, math, measurement)? | Defaults |
| Q-I12 | The t2 re-audit found the owner's **identity documents, CVs/applications and certificates** inside the corpus (mostly under `books\`). Should they stay in `D:\MBI-BRAIN` (the system will treat them as `restricted`, never processed), or will the owner move them out manually? | `restricted`: registered by metadata only, never processed or sent anywhere |
| Q-I13 | Should third-party reference documentation (Linux man-page HTML, Javadoc) be excluded from default ingestion (ADR-038), or indexed as a separate reference collection? | Excluded by default (ADR-038 PROPOSED) |

## NON-BLOCKING

| ID | Question |
|---|---|
| Q-N01 | Optional external bibliographic enrichment (DOI/ISBN metadata) later? |
| Q-N02 | Which other knowledge sources will be added after the university corpus (work notes, papers, books), and when? |
| Q-N03 | Is any UI beyond CLI, Obsidian and MCP desired (web UI)? |
| Q-N04 | Mobile access to the vault (Obsidian Sync or git)? |
| Q-N05 | Should semester and date metadata drive "outdatedness" judgments in gap analysis? |
| Q-N06 | Should the project be linked to Brain capability records (14_Capabilities) once capabilities mature? |
| Q-N07 | 13 PDFs are password-protected (12 Betriebslehre QualMan lectures). Does the owner have the passwords (referenced via the curation ledger, never stored in plain text), or should they be skipped? |
| Q-N08 | 42 files are unreadable (`Permission denied`, ACL-restricted). Should the owner fix read permissions so they can be processed? |
| Q-N09 | The Brain's own `CLAUDE.md` names `C:\Users\ammar\.claude\brain` as the Brain root, but that path does not exist; the global instructions use `D:\AgenticAI\My-Knowledge\brain`. Should the Brain docs be corrected (Brain maintenance, outside this project)? |
