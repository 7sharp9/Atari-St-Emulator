here=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)
export M68000_ROOT=$(cd "$here/../../.." && pwd)
export P=$M68000_ROOT/reversing/crudebuster/player
export CB_DIR=$M68000_ROOT/reversing/crudebuster/lua
export PY=$M68000_ROOT/.venv/bin/python
# cbrun <script|run> <lua> <seconds> ; set RUNX=run2 to use another run dir (parallel MAME runs need their own)
cbrun() { CB_RUN=$P/${RUNX:-run} $M68000_ROOT/reversing/crudebuster/cbmame.sh "$@"; }
