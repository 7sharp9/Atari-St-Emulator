#!/bin/sh
# d68.sh <hex addr> <n bytes>: 68000 linear listing of the cbuster program ROM dump
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../../.." && pwd)
exec "$root/.venv/bin/python" "$root/tools/disassemble.py" --rom "$root/scratchpad/crudebuster/rom/cbuster_main.bin" --base 0 --linear "$1" "$2"
