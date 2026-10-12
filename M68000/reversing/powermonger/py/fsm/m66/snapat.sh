#!/usr/bin/env bash
# snapat.sh <land> <cx> <cy> <prewait> <after> <out.snap>: the clickrun.sh input (no pokes), then run to the first $5106
# (prev $66 stamp, `u 5106 30000000`), step <after> more and save a snapshot.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT" || exit 1
land=$1; cx=$2; cy=$3; pre=$4; after=$5; out=$6
mv() { printf 'mouse move %s %s\ns 300000\nmouse move 0 0\ns 300000\n' "$1" "$2"; }
click() { printf 'mouse down l\nmouse move 0 0\ns 300000\nmouse up l\nmouse move 0 0\n'; }
{ printf 'disk scratchpad/powermonger.st\n'; [ "$pre" -gt 0 ] && printf 's %s\n' "$pre"
  mv -400 -400; mv 243 190; click; printf 's 300000\n'; mv $((cx - 243)) $((cy + 6 - 190)); click
  printf 'u 5106 30000000\n'; [ "$after" -gt 0 ] && printf 's %s\n' "$after"; printf 'snap %s\nq\n' "$out"; } |
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "scratchpad/pm143/lands/$land.snap" repl 2>&1 | grep -E 'reached|after|written'
