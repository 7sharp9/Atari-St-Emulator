#!/bin/sh
# dl.sh <addr> [count]: linear listing of the Final Fight program ROM
root=${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}
exec python3 "$root/tools/disassemble.py" --rom "$root/scratchpad/finalfight/ff_main.bin" --base 0 --linear "$1" "${2:-40}"
