#!/bin/sh
# mk.sh <lo> <hi> <root...> : rdis2 with the manual table ends in ends.txt
here=$(cd "$(dirname "$0")" && pwd)
args=""
for e in $(cat "$here/ends.txt"); do args="$args --end $e"; done
exec "$here/../../../../.venv/bin/python" "$here/rdis2.py" $args "$@"
