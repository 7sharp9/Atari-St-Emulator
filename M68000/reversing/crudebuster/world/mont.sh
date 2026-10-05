#!/bin/sh
# mont.sh <out.png> <cols> <files...> (scale 1 unless S set)
here=$(cd "$(dirname "$0")" && pwd)
out=$1; shift
exec env S=${S:-1} "$here/../../../../.venv/bin/python" "$here/py/montage.py" "$out" "$@"
