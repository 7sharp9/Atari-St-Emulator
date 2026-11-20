#!/bin/bash
# The Virus frontend gates (reversing/virus/frontend.md), captured afresh into $VIRUS_WORK/frontend/gate/.  About 6 minutes.
# Inputs: $W/drive/g_game2.snap, $W/fl/f1.snap, $W/demo/S1b.snap, $W/demo/death/long7.snap (drive.sh, the demo capture scripts).
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; M=reversing/virus/py/frontend; mkdir -p $W/frontend/gate
export VIRUS_WORK=$W
echo "== HUD: score, wave, best digits equal the font rendering (12 poked trials); control: the value+1 rendering"
uv run python $M/hud_match.py | tail -2
echo "== HUD icons: changed columns per lives/rockets step"
uv run python $M/hud_icons.py | tail -19
echo "== frame routines: flip and spin matrices (control: no-trap flip hits, rts-stub poke)"
uv run python $M/flip_spin.py | grep -E 'ok|FAIL|control'
echo "== sound: call-site sum over 300M steps of the demo"
uv run python $M/sound_sum.py | tail -2
echo "== sound: 120 stops at \$17932 against the static site table (control: ids + 1)"
uv run python $M/sound_verify.py | tail -2
echo "== game over: routine order from the last-life stop, and the hall-of-fame page against the RAM table"
uv run python $M/gameover_seq.py | tail -17
uv run python $M/hof_match.py | tail -1
