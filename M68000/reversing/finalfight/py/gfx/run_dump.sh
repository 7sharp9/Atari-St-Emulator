#!/bin/sh
# run_dump.sh <state> <tag> [frames] [seconds]  (env FF_POKE="addr=val,..." optional): fresh gfx/ram/regs/screenshot dumps from a saved state via ffrun.sh.
# Dumps go to scratchpad/finalfight/gfx/dump/, screenshots to scratchpad/finalfight/run/snap/<tag>_<k>.png.
# The state must be in scratchpad/finalfight/run/sta/ffightuc/<state>.sta (copy it there; never use stage/).
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out="$root/scratchpad/finalfight/gfx/dump"
mkdir -p "$out"
FF_POKE="$FF_POKE" FF_OUT="$out" FF_LOAD="$1" FF_TAG="$2" FF_FRAMES="${3:-3}" exec "$root/reversing/finalfight/ffrun.sh" "$here/gfxdump.lua" "${4:-400}"
