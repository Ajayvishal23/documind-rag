# Contributing

1. Fork and create a branch: `git checkout -b feat/hybrid-search`
2. Set up: `pip install -r requirements-dev.txt`
3. Make your change with tests in `tests/`
4. Check: `make lint && make test`
5. Commit using [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:` …)
6. Open a PR — the template will guide you

**Code style:** ruff (line length 120), type hints on public functions, no Streamlit imports
outside `app.py` and `src/documind/ui/`.
