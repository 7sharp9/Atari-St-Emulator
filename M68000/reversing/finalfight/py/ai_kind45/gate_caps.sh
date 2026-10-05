#!/bin/sh
# Spawn caps of $3e88 by callcap (fresh MAME run per call): for kind 4 and 5 and ranks 0, 4, 11, 19 (caps 1, 2, 3, 4 from the table
# $3efa + 32*(kind-3) + rank) call $3e88 with the kind in D0, rank word 168(A5) = rank and the kind's counter at -28331+(kind-3)(A5):
# counter = cap-1 must be accepted (D0 = 0, counter incremented), counter = cap must be refused (D0 = 1, counter unchanged).
# Kinds 0..2 share the counter -28332(A5) and the table $3eda. Needs AI45_RUN (see run.sh). Prints one line per call.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
OUT=${AI45_OUT:-$root/scratchpad/finalfight/p3/c/out}
mkdir -p "$OUT/capspec"
ok=0; bad=0
check() { # kind rank counter expect_ret(0 accept, 1 refuse) 
  kind=$1; rank=$2; cnt=$3; exp=$4
  if [ "$kind" -ge 3 ]; then addr=$((0xff8000 - 28331 + kind - 3)); else addr=$((0xff8000 - 28332)); fi
  spec=$OUT/capspec/c_${kind}_${rank}_${cnt}.lua
  printf 'return { addr = 0x3e88, warm = 200, regs = { D0 = 0x%x, A5 = 0xff8000 }, pokes = { {0x%x, %d, 2}, {0x%x, %d, 1} } }\n' "$kind" $((0xff8000 + 168)) "$rank" "$addr" "$cnt" > "$spec"
  res=$(CALLCAP_SPEC=$spec "$here/run.sh" callcap 2>&1 | grep 'callcap:')
  d0=$(echo "$res" | sed -n 's/.*regdelta D0 [0-9a-f]* \([0-9a-f]*\).*/\1/p')
  [ -z "$d0" ] && d0=$(printf '%08x' "$kind")
  got=$((0x$d0)); [ "$got" -ne 0 ] && [ "$got" -ne 1 ] && got=0   # unchanged D0 (= kind) means the routine returned moveq #0
  new=$(echo "$res" | grep -c "mem $(printf '%06x' "$addr")")
  if [ "$got" -eq "$exp" ]; then ok=$((ok+1)); echo "OK   kind $kind rank $rank counter $cnt -> D0=$got (expected $exp), counter changed: $new"; else bad=$((bad+1)); echo "FAIL kind $kind rank $rank counter $cnt -> D0=$got (expected $exp)"; echo "$res"; fi
}
for k in 4 5; do
  for r in 0 4 11 19; do
    case $r in 0) cap=1;; 4) cap=2;; 11) cap=3;; 19) cap=4;; esac
    check $k $r $((cap - 1)) 0
    check $k $r $cap 1
  done
done
echo "caps: $ok ok, $bad failed"
