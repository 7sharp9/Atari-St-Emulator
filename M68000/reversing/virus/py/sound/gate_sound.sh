#!/bin/bash
# The Virus sound gates (reversing/virus/frontend.md "Sound"), afresh into $VIRUS_WORK/sound/.  About 3 minutes.
# Inputs: $W/fl/f1.snap, $W/drive/g_game2.snap (capture.sh, drive.sh) and $W/aha.st.
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; M=reversing/virus/py/sound; rm -rf $W/sound; mkdir -p $W/sound
export VIRUS_WORK=$W
echo "== records: SoundEffectTable \$177d2 from f1.snap"
uv run python $M/dump.py $W/fl/f1.snap
echo "== model against Sound_Trigger/Sound_Tick: A every id alone, B 40 random streams"
uv run python $M/gate_sound.py | grep -E '^[AB] '
echo "== control shift2 (noise period >> 2)"
uv run python $M/gate_sound.py shift2 | grep -E '^[AB] '
echo "== control nonmax (noise written by every channel)"
uv run python $M/gate_sound.py nonmax | grep -E '^B '
echo "== control prio_ge (priority compare >=)"
uv run python $M/gate_sound.py prio_ge | grep -E '^B '
echo "== natural play: f1.snap 400 ticks, g_game2.snap 300 ticks; control shift2 on f1 100 ticks"
uv run python $M/gate_natural.py $W/fl/f1.snap 400 | tail -1
uv run python $M/gate_natural.py $W/drive/g_game2.snap 300 | tail -1
uv run python $M/gate_natural.py $W/fl/f1.snap 100 shift2 | tail -1
echo "== F# renderer (54 WAVs) against the model"
dotnet fsi $M/virus_sfx.fsx $W/sound/records.bin $W/sound/wav 3 | tail -1
uv run python $M/crosscheck.py
