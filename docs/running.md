# Running

Offline only. Python 3.12+ and no runtime dependencies.

```bash
pip install -e ".[dev]"
entagents list
entagents run <name>                       # demo input
entagents run <name> --input '<json>'      # your own input
entagents eval --out results/results.json  # exits non-zero if any safety probe fails
python scripts/render_docs.py              # regenerate pages, catalog JSON, README tables
pip install -e ".[board]" && python scripts/evidence_board.py
```

CI runs ruff, pytest, the printed test count, `render_docs.py --check` (which re-runs every eval), the hashed brand check and gitleaks over full history. CodeQL runs separately.

Test count: <!-- BEGIN:tests -->
**184 tests**
<!-- END:tests -->
