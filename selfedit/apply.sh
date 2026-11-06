#!/usr/bin/env bash
# Apply a KEPT proposal and commit it. Usage: selfedit/apply.sh [diff] [msg-file]
set -euo pipefail
cd "$(dirname "$0")/.."
DIFF="${1:-selfedit/out/proposal.diff}"
MSG="$(cat "${2:-selfedit/out/proposal.msg}")"
# defence in depth: only strategy/ may change
if grep -E '^(\+\+\+|---) ' "$DIFF" | grep -v '/dev/null' | sed -E 's#^(\+\+\+|---) (a/|b/)?##' | grep -vq '^strategy/'; then
  echo "refusing: diff touches outside strategy/"; exit 1
fi
git apply "$DIFF"
git add strategy
git -c user.name="Derezar Master" -c user.email="derezarmaster@gmail.com" commit -m "selfedit: $MSG"
