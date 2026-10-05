#!/bin/sh
# exp.sh <name> <level> <type hex> <var hex> [stop] [bot]   isolated passive/active probe: one enemy at 750, player at x=$PX y=$PY (hex, default 170/1c0)
# env overrides: EX (enemy x hex, default 1c0), EY (default 1c0), PX, PY, SX (scroll x, default 100), SY (scroll y, default 100), BTN, CB_BOT
here=$(cd "$(dirname "$0")" && pwd)
name=$1; lvl=$2; ty=$3; var=$4; stop=${5:-3500}; bot=${6:-0}
CB_LEVEL=$lvl CB_STOP=$stop CB_BOT=$bot CB_NOSCRIPT=1 CB_SPAWN="750:$ty:$var:${EX:-1c0}:${EY:-1c0}" CB_PLAYER="745:${PX:-170}:${PY:-1c0}" CB_SCROLL="745:${SX:-100}:${SY:-100}" "$here/run.sh" probe.lua "$name" 2>&1 | tail -1
