#!/usr/bin/env bash
# track.sh <src.snap> <name> <nframes> <addr:len>...  : dump memory ranges at each of N successive $f898 frames
src=$1; name=$2; n=$3; shift 3
d=${PM_WORK:-scratchpad/pmwork}/trk; mkdir -p $d
{ echo "u f898 5000000"
  for i in $(seq 1 $n); do for a in "$@"; do echo "m ${a%%:*} ${a##*:}"; done; echo "bpc f898 1 5000000"; done; echo q; } > $d/$name.cmds
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $src repl --disk-a scratchpad/powermonger.st < $d/$name.cmds 2>&1 | grep -E "^([0-9a-f]{2} )+[0-9a-f]{2}\s*$" > $d/$name.txt
wc -l $d/$name.txt
