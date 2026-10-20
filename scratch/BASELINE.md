# Stage 0 baseline (before any change)
branch ccr-9a8a26e1-b0l7bh = origin/main 5fa91ac + fast-forward merge of claude/serene-dijkstra-2awdy9 (064148f)
lint (scripts/lint.sh): clean — ruff ok, format ok, mypy "Success: no issues found in 47 source files"
headless suite: ZENDRIVER_TEST_BROWSERS=headless uv run pytest -n 4 -p no:cacheprovider
  -> 118 passed, 1 skipped (test_drm.py:23 Widevine) in 35.55s, no failures
