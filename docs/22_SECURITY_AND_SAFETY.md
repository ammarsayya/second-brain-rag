# 22 — Security and Safety

## 1. Source protection (HC-01/03, ADR-002)

- **SourceFS** is the only module that touches source roots. It opens files read-only (`rb`), never calls write, rename, delete or chmod,
  and refuses paths outside the configured roots (path normalization, `\\?\` long paths, no symlink escapes).
- A lint test forbids `os.remove`, `os.rename`, `shutil.move`, `Path.unlink`, `open(..., 'w')` etc. on any path derived from a source root outside
  allow-listed modules (static grep test + runtime guard).
- A runtime guard in tests monkeypatches filesystem mutators and asserts zero calls against source roots during full pipeline runs on fixtures.
- Optional OS hardening: the owner may set a read-only ACL for the sbr process user on `D:\MBI-BRAIN` (documented, not required).
- `sbr doctor` compares a sample of source (size, mtime, hash) against the registry to detect *unexpected* changes, which would indicate a bug or an external change.

## 2. Vault protection (HC-07/08)

The VaultWriter rules (19 §2), git commits per batch, and tests TS-VAULT-* (edit detection, fork behavior, no writes to `notes/`).

## 3. Sensitive data (ADR-035, NFR-09)

- **Sensitivity classes:** `normal`, `personal` (owner's own contracts, reports, personal data), `third_party_personal` (grade lists
  with other students, e.g. `Labornoten`, `Ergebnislisten`), `restricted` (owner-marked).
- The t2 re-audit (docs/37) found the owner's **identity documents, CVs/applications and certificates** (including a third party's) in the corpus. Default rule: `restricted` (registered by metadata only, never processed, never sent anywhere, counts-only reporting; Q-I12).
- Classification: path and name rules (Vertrag, Noten (excluding "Knoten"), Ergebnisliste, Bewerbung, Lebenslauf, Zeugnis, Ausweis, Immatrikulation …) + content signals (tables of names + grades) +
  owner overrides in `curation/sensitivity_overrides.yaml`.
- **Policy:** `third_party_personal` → registered but **not processed beyond metadata** by default (Q-I04). `personal` → processed locally.
  It is sent to remote models only if the role config allows it. The gateway enforces this per call using the chunk or document sensitivity.
- Logs and traces redact sensitive content (hashes plus truncated text only).

## 4. Copyright and licensing

Most sources are copyrighted textbooks and lecture materials, used privately. Rules:
- The vault and its derived content are **private**. Git remotes for the vault must be private (Q-I09).
- `audit/` and `var/` are never published. They contain paths and derived content.
- External research stores copies for provenance with license notes. It does not redistribute them.
- Sending textbook content to cloud models or OCR APIs is a policy decision (Q-B03). The gateway has a per-root switch.

## 5. Secrets

API keys come from environment variables or the OS keychain via config references. They are never written to repo files, logs or the vault.
A pre-commit secret scan runs on the project repo.

## 6. External research safety

Fetchers use timeouts, size limits and content-type checks. Downloaded files are **never executed**. PDFs are parsed with the same sandboxed extractors.
Prompt-injection defense: fetched content is treated as data. The research agent's tools cannot write to the vault or indexes except through
the approval path. Instructions found in documents are ignored and flagged.

## 7. Archive and file safety

No execution of `.exe`, `.bat`, `.jar` or `.sh` from the corpus. Archive extraction has limits (08 §6). The Office parsers disable macros and external links.
