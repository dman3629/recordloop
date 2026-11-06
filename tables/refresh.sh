#!/usr/bin/env bash
# Re-fetch the codetables.de bounds. Run from anywhere; writes next to this script.
set -euo pipefail
cd "$(dirname "$0")"
python3 fetch_codetables.py
