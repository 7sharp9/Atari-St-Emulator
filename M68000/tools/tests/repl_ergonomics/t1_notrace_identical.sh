#!/bin/bash
# Change 1, compatibility: with ATARI_NOTRACE=1 two builds give byte-identical stdout and stderr for a
# 2M-step cold boot and for a REPL script (commands whose behaviour did not change).
# usage: t1_notrace_identical.sh <base.dll> <new.dll>
[ $# -eq 2 ] || { echo "usage: $0 <base.dll> <new.dll>"; exit 2; }
A=$1; B=$2
. "$(dirname "$0")/common.sh" "$B"
case "$A" in /*) ;; *) A="$M/$A" ;; esac
echo "base: $A ($(shasum -a 256 "$A" | cut -c1-12))"
cat > "$OUT/script.txt" <<'EOF'
s 100000
r
m fc0000 32
hits 50000 fc0030 fc0000 fc00d4
bt
watch 600 4
s 400000
unwatch
kbd 39
s 30000
kbd b9
s 30000
bp fc0030 100000
r
q
EOF
for t in base new; do
    d=$A; [ $t = new ] && d=$B
    ATARI_NOTRACE=1 dotnet exec "$d" 2000000 > "$OUT/boot_$t.out" 2> "$OUT/boot_$t.err"
    ATARI_NOTRACE=1 dotnet exec "$d" 1 repl < "$OUT/script.txt" > "$OUT/repl_$t.out" 2> "$OUT/repl_$t.err"
done
wc -c "$OUT"/*.out "$OUT"/*.err
echo "repl stdout (new), first 15 lines:"; head -15 "$OUT/repl_new.out"
check "2M boot stdout identical" cmp "$OUT/boot_base.out" "$OUT/boot_new.out"
check "2M boot stderr identical" cmp "$OUT/boot_base.err" "$OUT/boot_new.err"
check "REPL stdout identical" cmp "$OUT/repl_base.out" "$OUT/repl_new.out"
check "REPL stderr identical" cmp "$OUT/repl_base.err" "$OUT/repl_new.err"
check "REPL stdout is not empty (positive control)" [ -s "$OUT/repl_new.out" ]
finish
