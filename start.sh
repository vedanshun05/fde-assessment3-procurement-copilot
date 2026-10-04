#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
if [[ ! -f .venv/.dependencies-ready ]] || [[ requirements.lock.txt -nt .venv/.dependencies-ready ]]; then
  .venv/bin/python -m pip install -r requirements.lock.txt
  touch .venv/.dependencies-ready
fi
exec .venv/bin/python run_local.py "$@"
