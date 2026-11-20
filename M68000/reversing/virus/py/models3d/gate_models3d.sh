#!/bin/bash
# The Virus model drawers (reversing/virus/README.md "Model data and the model drawers"), afresh into $VIRUS_WORK/models3d/.
# Inputs: $W/fl/f1.snap, $W/chain/long100/starts/main_g050.snap.  About 40 seconds.
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; M=reversing/virus/py/models3d; rm -rf $W/models3d; mkdir -p $W/models3d
export VIRUS_WORK=$W
echo "== natural frames: f1.snap 4000 stops, main_g050 6000 stops; control (matrix transposed) on f1"
uv run python $M/gate_model.py $W/fl/f1.snap 4000 | grep -E '^(model|control) '
uv run python $M/gate_model.py $W/chain/long100/starts/main_g050.snap 6000 | grep -E '^(model|control) '
uv run python $M/gate_model.py $W/fl/f1.snap 4000 --control | grep -E '^(model|control) '
echo "== all 43 models in 40 random poses from f1.snap; control"
uv run python $M/gate_all_models.py $W/fl/f1.snap 40 | grep -E '^vertex'
uv run python $M/gate_all_models.py $W/fl/f1.snap 40 --control | grep -E '^vertex'
echo "== SVG renders"
uv run python $M/dump_data.py $W/fl/f1.snap $W/models3d
dotnet fsi $M/virus_models.fsx -- $W/models3d/models.bin $W/models3d/palette.txt $W/models3d/svg | tail -1
ls $W/models3d/svg | grep -c '^model_.*svg$'
