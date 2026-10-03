#!/bin/bash
# Season fade + weather count run. Usage: season_run.sh <tag> <season 0|2|4|6> [steps] [snap]
# Pokes $57ff6 := $0681 (the unique predecessor of 0 under x*$24a1+$24df mod $2000, so the
# first $1abaa call wraps) and $57fd0 := <season> (the season BEFORE the wrap), then counts hits.
# Output: $SEASON_OUT/<tag>.{cmds,txt} (default scratchpad/season). Always ATARI_NOTRACE=1.
ROOT="${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}"; cd "$ROOT" || exit 1
TAG=$1; SEAS=$2; STEPS=${3:-125000000}; SNAP=${4:-scratchpad/pm142/rand1.snap}
OUT=${SEASON_OUT:-scratchpad/season}; mkdir -p "$OUT"
# $57fd0 is followed by the word $0188 in rand1.snap ($57fd2): keep it, w writes a longword.
cat > "$OUT/$TAG.cmds" <<EOF
w 57ff6 06810001
w 57fd0 000${SEAS}0188
hits $STEPS 1abaa 1ac3c 1ad74 1ad82 1ad8c 1ad40 1ad4a 1ad54 1a856 1acc8 1acec 1ad06 1ad20 1ba3e 1aacc
m 57fd0 2
m 57fec 2
m 4bb42 4
q
EOF
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$OUT/$TAG.cmds" > "$OUT/$TAG.txt" 2>&1
