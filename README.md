# second-brain-rag (`sbr`)

A local-first agentic RAG second brain over the owner's university corpus.
The source corpus is read-only evidence and is never modified by this system.

Project documentation lives in [`docs/`](docs/00_PROJECT_OVERVIEW.md).
Agent operating rules are in [`CLAUDE.md`](CLAUDE.md).

## Development

```powershell
uv sync                     # Python 3.12 environment with dev tools
uv run sbr --help
powershell -File tools/check.ps1   # lint + format check + types + tests
python tools/validate_plan.py      # plan consistency (must print PLAN CONSISTENT)
```
