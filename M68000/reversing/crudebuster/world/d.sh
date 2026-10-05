#!/bin/sh
# d.sh <hexaddr> <ninsns> : linear 68000 disassembly of the cbuster dump
r=$(cd "$(dirname "$0")/../../../.." && pwd)
exec "$r/.venv/bin/python" "$r/tools/disassemble.py" --rom "$r/scratchpad/crudebuster/rom/cbuster_main.bin" --base 0 --linear "$1" "$2"
