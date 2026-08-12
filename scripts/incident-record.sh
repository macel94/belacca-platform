#!/usr/bin/env bash
# Explicit local-only incident record entrypoint.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
exec python3 "$root/scripts/incident_record.py" "$@"
