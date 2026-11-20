#!/bin/bash
# Populous II: hits on every entity-state handler of update_entities $2309a over STEPS steps from each snapshot.
# The word table $2311c has 36 entries, states 0..$46 (state 2's handler $23164 starts right after it); several
# states share a handler, so a count is per handler and is labelled with every state that maps to it.
# One line per snapshot: ticks, then states:count for every handler that ran.
# Run from anywhere:  bash reversing/populous2/py/state_census.sh <steps> <snap>...
set -e
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done; cd "$d"
STEPS=$1; shift
MAP=$(uv run python - <<'PY'
d = open("scratchpad/populous2/pop2_1770.bin", "rb").read()
w = lambda a: (d[a - 0x1770] << 8) | d[a - 0x1770 + 1]
h = {}
for i in range(36):
    v = w(0x2311C + 2 * i)
    h.setdefault(0x2311C + (v - 0x10000 if v & 0x8000 else v), []).append(f"{2 * i:x}")
print(" ".join(f"{a:x}:{'/'.join(s)}" for a, s in sorted(h.items()) if a != 0x2311C))
PY
)
H="2309a $(echo "$MAP" | tr ' ' '\n' | cut -d: -f1 | tr '\n' ' ')"
for s in "$@"; do
  printf 'hits %s %s\nq\n' "$STEPS" "$H" |
    ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$s" repl > "$s.states.log" 2>&1 &
done
wait
for s in "$@"; do
  awk -v n="$(basename "$s")" -v map="2309a:tick $MAP" 'BEGIN { split(map, t, " ");
           for (i in t) { split(t[i], p, ":"); nm["$0" p[1]] = p[2] } }
       /^  \$0/ { if ($2 > 0) out = out " " nm[$1] ":" $2 }
       END { print n ":" out }' "$s.states.log"
done
