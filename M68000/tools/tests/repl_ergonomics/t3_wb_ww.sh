#!/bin/bash
# Change 3: `wb <addr> <hexbyte>` and `ww <addr> <hexword>` write one byte / one word and leave the
# neighbouring bytes alone; `w` still writes a longword. An oversized value or an odd `ww` address is
# a REPL error. Both commands are in `help`.
# usage: t3_wb_ww.sh [dll]
. "$(dirname "$0")/common.sh"
cat > "$OUT/script.txt" <<'EOF'
w 1000 11223344
m 1000 4
wb 1001 aa
m 1000 4
ww 1002 bbcc
m 1000 4
w 1000 01020304
m 1000 4
wb 1000 1ff
ww 1001 1234
m 1000 4
help
EOF
ATARI_NOTRACE=1 dotnet exec "$DLL" 1 repl < "$OUT/script.txt" > "$OUT/repl.out" 2> "$OUT/repl.err"
rc=$?
echo "exit status $rc"; echo "--- stdout (help line cut to its w/wb/ww part)"
sed -E 's/.*(w <hexaddr> <hexvalue>[^,]*,[^,]*,[^,]*,).*/help: ... \1 .../' "$OUT/repl.out"; echo "--- stderr"; cat "$OUT/repl.err"
dumps=$(grep -E '^([0-9a-f]{2} ){3}[0-9a-f]{2}$' "$OUT/repl.out" | tr '\n' '|')
echo "dumps: $dumps"
check "w, wb, ww, w read back as expected" [ "$dumps" = '11 22 33 44|11 aa 33 44|11 aa bb cc|01 02 03 04|01 02 03 04|' ]
check "wb 1000 1ff is rejected" grep -q -F 'REPL error: 9: wb 1000 1ff' "$OUT/repl.err"
check "ww at an odd address is rejected" grep -q -F 'REPL error: 10: ww 1001 1234' "$OUT/repl.err"
check "help names wb and ww" grep -q -F 'wb <hexaddr> <hexbyte> = write a byte, ww <hexaddr> <hexword> = write a word' "$OUT/repl.out"
finish
