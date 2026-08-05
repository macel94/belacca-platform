#!/usr/bin/env bash
# Explicit entrypoint for a bounded, read-only evidence collection.
set -euo pipefail

root=$(git rev-parse --show-toplevel)
exec python3 "$root/scripts/incident_evidence.py" "$@"
