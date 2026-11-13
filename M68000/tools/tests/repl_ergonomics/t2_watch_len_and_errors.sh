#!/bin/bash
# Change 2: `watch <addr> <len>` takes len as decimal, `$hex` or `0xhex`; a bare hex-looking len
# (`a400`) and any other malformed line is a REPL error that does not end the run: the lines after it
# still execute, and the exit status at EOF is 1.
# usage: t2_watch_len_and_errors.sh [dll]
. "$(dirname "$0")/common.sh"
cat > "$OUT/script.txt" <<'EOF'
watch 40000 $a400
watch 40000 0xa400
watch 40000 41984
watch 40000 a400
s zz
frobnicate 1
w 1000 cafef00d
m 1000 4
EOF
ATARI_NOTRACE=1 dotnet exec "$DLL" 1 repl < "$OUT/script.txt" > "$OUT/repl.out" 2> "$OUT/repl.err"
rc=$?
echo "exit status $rc"; echo "--- stdout"; cat "$OUT/repl.out"; echo "--- stderr"; cat "$OUT/repl.err"
want='Watching [$00040000,$0004a3ff]'
check "\$a400, 0xa400 and 41984 all watch [\$40000,\$4a3ff]" [ "$(grep -c -F "$want" "$OUT/repl.out")" -eq 3 ]
check "a400 is reported as a bad operand on line 4" grep -q -F 'REPL error: 4: watch 40000 a400: bad operand' "$OUT/repl.err"
check "line 5 (s zz) and line 6 (unknown command) are reported" [ "$(grep -c -E '^REPL error: (5|6):' "$OUT/repl.err")" -eq 2 ]
check "the lines after the errors still ran (w + m read back cafef00d)" grep -q -x 'ca fe f0 0d' "$OUT/repl.out"
check "exit status 1 after errors" [ "$rc" -eq 1 ]
finish
