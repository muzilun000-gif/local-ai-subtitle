#!/bin/bash
cd "$(dirname "$0")" || exit 1
PYTHON=""
for candidate in python3.12 python3.11 python3.13 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)' >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "Please install Python 3.11 or 3.12: https://www.python.org/downloads/"
  read -r -p "Press Enter to close..."
  exit 1
fi
"$PYTHON" tools/launch.py "$@"
status=$?
if [ "$status" -ne 0 ]; then read -r -p "Press Enter to close..."; fi
exit "$status"
