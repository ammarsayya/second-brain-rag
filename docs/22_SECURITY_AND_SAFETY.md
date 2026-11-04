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
- Classification: path and name rules (Vertrag, Noten (excluding "Knoten"), Ergebnisliste, Bewerbung, Lebenslauf, Zeugnis, Ausweis, Immatrikulation, and since rules version 2 (2026-11-04) court/legal-aid papers: Terminsladung, Prozesskostenhilfe/PKH, Gerichtsbeschluss, Aktenzeichen …) + content signals (tables of names + grades) +
  owner overrides in `curation/sensitivity_overrides.yaml`.
- **Policy:** `third_party_personal` → registered but **not processed beyond metadata** by default (Q-I04). `personal` → processed locally.
  It is sent to remote models only if the role config allows it. The gateway enforces this per call using the chunk or document sensitivity.
- Logs and traces redact sensitive content (hashes plus truncated text only).
- Evaluation/spike tools that open source content go through `sbr.eval.spike_gate.processable_blobs` (active, not `restricted`/`third_party_personal`, current path rules re-applied to every alias). They report gated blobs as a count only.

## 4. Copyright and licensing

Most sources are copyrighted textbooks and lecture materials, used privately. Rules:
- The vault and its derived content are **private**. Git remotes for the vault must be private (Q-I09).
- `audit/` and `var/` are never published. They contain paths and derived content.
- External research stores copies for provenance with license notes. It does not redistribute them.
- Sending textbook content to cloud models or OCR APIs is a policy decision (Q-B03). **Answered 2026-11-04: not allowed in the current phase (ADR-039, local-only).** The gateway refuses every non-loopback provider (T-P7-01).

## 5. Secrets

API keys come from environment variables or the OS keychain via config references. They are never written to repo files, logs or the vault.
A pre-commit secret scan runs on the project repo.

## 6. External research safety

Fetchers use timeouts, size limits and content-type checks. Downloaded files are **never executed**. PDFs are parsed with the same sandboxed extractors.
Prompt-injection defense: fetched content is treated as data. The research agent's tools cannot write to the vault or indexes except through
the approval path. Instructions found in documents are ignored and flagged.

## 7. Archive and file safety

No execution of `.exe`, `.bat`, `.jar` or `.sh` from the corpus. Archive extraction has limits (08 §6). The Office parsers disable macros and external links.

## 8. Model egress (T-P7-01, ADR-039/ADR-040)

Remote model providers are not authorized (owner decisions Q-B03/Q-B04, 2026-11-04).

**Enforced by sbr code (tested in `tests/models/`):**
- Configuration: `models.allow_remote` can only be `false`, including via `SBR_MODELS__ALLOW_REMOTE`. Every provider `base_url` must be `http(s)` on `localhost` or a loopback IP literal, with no credentials, query or fragment. Unknown provider kinds and literal API keys are rejected; `api_key_env` takes only a variable name.
- Gateway: an adapter that is not declared `LOCAL` is refused at construction (the base adapter class defaults to `REMOTE`, so a new adapter fails closed). Fallbacks are local by construction. `restricted` content is refused for every role, before any provider is contacted.
- Local adapter, on every call: the host must resolve to loopback addresses only; `HTTP(S)_PROXY` variables are ignored; redirects are refused, never followed; responses have a size cap and a deadline. Error messages never include the server's response body.
- Logs and call records hold hashes, sizes and ids, never prompt or output text.

**Not enforced by sbr; this is the deployment's or operating system's responsibility:**
- Other code in the same process (third-party libraries, future adapters) opening sockets. The gateway only controls the connections its own adapters make.
- The local inference server's own egress. For example, an Ollama instance may pull model weights from the internet. Running a server is the owner's choice and outside sbr.
- Tampering with `/etc/hosts` or the resolver, and other local processes listening on loopback ports.
- A real network sandbox (macOS firewall, a pf rule, or a container without network). Recommended if a hard guarantee is needed.
