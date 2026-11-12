#!/bin/bash
# Gate for the renderer (render.md): sine table, rotations, projection, back-face test and span filler,
# each against callcap runs from c_s30.snap. Prints one count line per proof.
set -e
here=$(cd "$(dirname "$0")" && pwd)
root=$here; while [ ! -f "$root/tools/rdis.py" ]; do root=$(dirname "$root"); done
cd "$root"
uv run python -I "$here/sine_gate.py" | head -1
uv run python -I "$here/rot_gate.py" | grep match
uv run python -I "$here/proj_gate.py" | grep 'projection match'
uv run python -I "$here/face_gate.py" | grep 'face test match'
uv run python -I "$here/span_gate.py" | grep 'span model match'
