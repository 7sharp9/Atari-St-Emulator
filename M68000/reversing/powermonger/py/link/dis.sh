#!/bin/bash
# usage: dis.sh LO HI [snap]   (hex without 0x); disassembles the whole image listing
cd "${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}" || exit 1
S=${3:-scratchpad/pm123/win/m1_win.snap}
uv run python tools/disassemble.py --snap "$S" --all "$1" "$2"
