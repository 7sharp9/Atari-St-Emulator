#!/bin/bash
# Rebuild the infographic from the emulator: every run, then the page. Run from M68000/ with scratchpad/lemmings/sel.snap
# and lemmings.st in place (reversing/lemmings/drive.txt, click_digger.txt). Output: scratchpad/lemmings/info/inside_lemmings.html
set -e
cd "$(dirname "$0")/../../.."
reversing/lemmings/infographic/runs.sh
python3 reversing/lemmings/infographic/blockerarms.py scratchpad/lemmings/info/runs/blocker
python3 reversing/lemmings/infographic/gather.py
