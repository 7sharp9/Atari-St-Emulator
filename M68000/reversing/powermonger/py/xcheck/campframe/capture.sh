#!/bin/bash
# usage: capture.sh <snap> <tag> [stops]
# Stops at every a_object $117b0 entry (byte6 6 and 24 records), steps one instruction (D4.b = byte 7),
# dumps $57fec and the marker pool $4cff8..$4d250 (10-byte records, byte 6 category), then runs to the shared rts $1184c and prints D2 (the frame the caller blits).
# Output: $PM_WORK/campframe/<tag>.out ; parse with parse.py
set -e
here=$(cd "$(dirname "$0")" && pwd); root=$here
while [ ! -f "$root/tools/rdis.py" ]; do root=$(dirname "$root"); [ "$root" = / ] && { echo "no repo root"; exit 1; }; done
cd "$root"
snap=$1; tag=$2; n=${3:-60}
out=${PM_WORK:-scratchpad/pm162}/campframe; mkdir -p "$out"
{
  echo "disk scratchpad/powermonger.st"
  for i in $(seq "$n"); do
    echo "bp 117b0 3000000"
    echo "s 1"
    echo "r"
    echo "m 57fec 2"
    echo "m 4cff8 600"
    echo "bp 1184c 400"
    echo "s 1"
  done
  echo q
} > "$out/$tag.repl"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$snap" repl < "$out/$tag.repl" > "$out/$tag.out" 2>/dev/null
echo "wrote $out/$tag.out"
