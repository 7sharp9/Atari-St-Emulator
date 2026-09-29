#!/bin/zsh
# usage: tl.sh <snap rel to scratchpad/impossamole> <slot> <frames> [poke lines...]
cd "${0:A:h}/../../../.."
s=$1; shift
uv run python reversing/impossamole/py/spawn/timeline.py scratchpad/impossamole/$s "$@" | cut -c1-235
