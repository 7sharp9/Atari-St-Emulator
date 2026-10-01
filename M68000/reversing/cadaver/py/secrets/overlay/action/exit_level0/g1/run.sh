#!/bin/zsh
# run.sh <script.py> <args...>: run a G1 script with the repo environment (the master route_level0_exit.py sets the same variables itself).
export M68000_ROOT="$(cd "$(dirname "$0")/../../../../../../../.." && pwd)"
export ATARI_NOTRACE=1
exec $M68000_ROOT/.venv/bin/python "$@"
