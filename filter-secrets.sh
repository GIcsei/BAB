#!/usr/bin/env bash
# filter-secrets.sh — Purge all known secrets from git history.
#
# Prerequisites:
#   pip install git-filter-repo
#
# Usage (run from a FRESH clone):
#   git clone https://github.com/GIcsei/BAB.git BAB-clean
#   cd BAB-clean
#   bash filter-secrets.sh
#
# After running:
#   git remote add origin https://github.com/GIcsei/BAB.git   # if removed
#   git push --force --all origin
#   git push --force --tags origin
#
# Then have every contributor delete their old clone and re-clone.
# Open a GitHub support ticket to request server-side GC of unreachable objects.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Step 1: Removing credential file from all history..."
git filter-repo \
    --invert-paths \
    --path app/REDACTED_CREDENTIAL_FILE.json \
    --path "app/REDACTED_CREDENTIAL_FILE.json:Zone.Identifier" \
    --force

echo "==> Step 2: Replacing sensitive strings in all remaining blobs..."
git filter-repo \
    --replace-text "${SCRIPT_DIR}/replacements.txt" \
    --force

echo ""
echo "==> Done. Verify by searching for sensitive strings — all should return empty."
echo "    Then force-push all branches and tags."
