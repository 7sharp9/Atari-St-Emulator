#!/bin/bash
# Gate for README "Hidden keys and leftovers" and ai.md section 7's cheat extras: every key trial against its no-key
# control, and the exception handler reached only with the vector moved (hidden.py).
here=$(cd "$(dirname "$0")" && pwd)
root=$here; while [ ! -f "$root/tools/rdis.py" ]; do root=$(dirname "$root"); done
py="uv run --project $root python -I"
cd "$root"
$py "$here/hidden.py" keys | grep 'keys .* control'
$py "$here/hidden.py" andy | grep '^andy'
