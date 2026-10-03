#!/bin/bash
# One weather spell: watch every write of $4bb44 (the spell counter) for 40M steps from rand1.snap after
# a forced season wrap, plus hits on $1aacc (dead), $1ad74 (spell start), $1ad4a (end), $1ad40 (draws).
# Expected (summer -> autumn rain): $4bb44 := $40 at step 854056250-ish (watch prints absolute steps), 65 draws, ends $ffff;
# hits: $1aacc 0, $1ad74 1 @25302965, $1ad4a 1 @36808977, $1ad40 65.
ROOT="${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}"; cd "$ROOT" || exit 1
OUT=${SEASON_OUT:-scratchpad/season}; mkdir -p "$OUT"
cat > "$OUT/spell_watch.cmds" <<EOF
w 57ff6 06810001
w 57fd0 00040188
watch 4bb44 2
hits 40000000 1aacc 1ad74 1ad4a 1ad40
m 4bb42 6
q
EOF
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm142/rand1.snap repl < "$OUT/spell_watch.cmds" > "$OUT/spell_watch.txt" 2>&1
