#!/usr/bin/env bash
# Save pytest + vitest logs to docs/E2E_EVIDENCE/test-outputs/
# Run from repo root: bash scripts/capture-test-results.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docs/E2E_EVIDENCE/test-outputs"
mkdir -p "$OUT"

PY="$ROOT/backend/venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

echo "== pytest (backend) =="
cd "$ROOT/backend"
EXTRA=()
if "$PY" -c "import pytest_html" 2>/dev/null; then
  EXTRA=(--html="$OUT/pytest-report.html" --self-contained-html)
  echo "(pytest-html: also writing HTML)"
fi
"$PY" -m pytest . -v --tb=short "${EXTRA[@]}" 2>&1 | tee "$OUT/pytest-output.txt"

if [[ ! -f "$OUT/pytest-report.html" ]]; then
  echo "No HTML: pip install pytest-html to enable"
fi

echo "== vitest (frontend) =="
cd "$ROOT/frontend"
npm run test:run 2>&1 | tee "$OUT/vitest-output.txt"

echo "Done: $OUT"
