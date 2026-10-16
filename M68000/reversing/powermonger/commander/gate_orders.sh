#!/usr/bin/env bash
# gate_orders.sh - do the player orders work when injected into an AI side's command slot? (commander README step 1,
# extended from gate_inject.sh's attack $0c to the rest of the order set). From pm142/rand1.snap, one arm per order, all
# at the same step budget; side 3 (an AI side) has its slot $58028 at state 2 (the AI silent) and $58042[3] names the
# acting group ($400 group 0, run at once; $402 group 1, by carrier pigeon). Slot bytes 1..3 = type, x, y (or a param word).
#   ctl       no order, slot watched                     ctlL  no order, group 0's lead watched (control of the targeted arms)
#   post      $16 00 04  posture 4 (passive)              $6cc6 -> $35a0
#   postpg    as post, acting group 1: by pigeon         $4562 takes the slot ($45d0); $6cc6 -> $35a0 when it lands
#   xfer      $04 02 00  men from group 1 to group 0      $6ba8 -> $1c18
#   dismiss   $14 00 00                                  $6cbc -> $1cc4
#   dropf     $12 00 00  drop food                       $6c96 -> $39d4 D7=1
#   drope     $18 00 00  drop equipment (12 boats)        $6cda -> $39d4 D7=2
#   targeted ($3154 sender: lead 30 := arrival mode at $3236; arrival: lead 31 := 30 at $14fdc):
#   spy       $20 27 3d  side 2's lord 11 town (39,61)    $6d56 -> $3154 + $1d36, mode $7a -> $3da4
#   ally      $1e 27 3d  side 2's lord 11 town (39,61)    $6d32 -> $3154, mode $76 -> $33b0 -> side 2 posts $2a ($3458) -> $34a8
#   food      $06 21 46  own lord 12 town (33,70)         $6bbe -> $3154, mode $1a -> $150c0
#   men       $08 21 46  own lord 12 town (33,70)         $6bea -> $3154, mode $1c -> $15122 (lead mode $28, the join wait)
#   invent    $0e 21 46  own lord 12 town (33,70)         $6c48 -> $3154, mode $22 -> $5fa0 -> $5cde
#   equip     $10 21 46  own lord 12 town (33,70)         $6c6a -> $3154, mode $6e -> $61f8
#   trade     $1c 21 46  own lord 12 town (33,70)         $6d12 -> $3154, mode $78 -> $63f4
#   supply    $1a 21 48  cell (33,72)                     $6d00 -> $390e (lead 30 := $74 at $3948), mode $74 -> $3956
# Usage (from anywhere under M68000/): gate_orders.sh [arm...]   (no args: every arm, then the check)
#   BUDGET (default 40000000 steps; about 10 s an arm), PAR (parallel runs, default 4), CMD_WORK (default scratchpad/cmd1):
#   writes $CMD_WORK/orders/. CHECK_ONLY=1 re-runs the check on existing outputs.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); done; cd "$ROOT"
W=${CMD_WORK:-scratchpad/cmd1}/orders; mkdir -p "$W"
SNAP=scratchpad/pm142/rand1.snap
BUDGET=${BUDGET:-40000000}; PAR=${PAR:-4}
# handlers, their callees, the pigeon, and every arrival executor named in strategy.md "What each order does"
HITS="6b8e 6ba8 6bbe 6bea 6c48 6c6a 6c96 6cbc 6cc6 6cda 6d00 6d12 6d32 6d56 3154 3248 38ce 6128 35a0 1d36 1c18 1cc4 39d4 390e 4562 150c0 15122 151a8 5fa0 5cde 15740 61f8 15772 63f4 15754 33b0 3458 34a8 1578c 3da4 160d6 3956 35f4 6822"
G0="w 58048 0400053c"; G1="w 58048 0402053c"; ST2="w 5802c 02000400"   # longwords: keep side 4's $53c and its slot bytes 04 00
pokes() { # arm -> its REPL poke lines
  local o
  case $1 in
    ctl|ctlL) o=03000000;; post|postpg) o=03160004;; spy) o=0320273d;; ally) o=031e273d;; food) o=03062146;;
    men) o=03082146;; invent) o=030e2146;; equip) o=03102146;; trade) o=031c2146;; xfer) o=03040200;;
    dismiss) o=03140000;; dropf) o=03120000;; drope) o=03180000;; supply) o=031a2148;;
    *) echo "unknown arm $1" >&2; exit 2;;
  esac
  if [ "$1" = postpg ]; then echo "$G1"; else echo "$G0"; fi
  echo "w 58028 $o"; echo "$ST2"
  case $1 in   # the REPL keeps one watch range: the slot, or for a targeted order side 3 group 0's lead bytes 30/31
    ctlL|spy|ally|food|men|invent|equip|trade|supply) echo "watch 53b5a 2";;   # lead $1fd6: $51b66 + $1fd6 + 30
    *) echo "watch 58028 6";;
  esac
}
run() { # arm
  local arm=$1
  { echo "disk scratchpad/powermonger.st"; pokes "$arm"; echo "hits $BUDGET $HITS"; echo "snap $W/$arm.snap"; echo q; } > "$W/$arm.repl"
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$W/$arm.repl" > "$W/$arm.out" 2> "$W/$arm.err"
}
ALL="ctl ctlL post postpg xfer dismiss dropf drope spy ally food men invent equip trade supply"
if [ -z "${CHECK_ONLY:-}" ]; then
  n=0
  for a in ${@:-$ALL}; do
    run "$a" & n=$((n + 1))
    if [ $((n % PAR)) -eq 0 ]; then wait; fi   # bash 3.2 (macOS) has no wait -n: run in batches of PAR
  done
  wait
fi
uv run python - "$W" <<'EOF'
import re, struct, sys, os
sys.path.insert(0, 'tools')
from disassemble import ram_from_snap
w = sys.argv[1]
RAM = {}
def ram(arm):
    if arm not in RAM: RAM[arm] = ram_from_snap(f'{w}/{arm}.snap')
    return RAM[arm]
def hits(arm, a):
    m = re.search(rf'\${a:06x}\s+(\d+)', open(f'{w}/{arm}.out').read()); return int(m.group(1))
h = lambda r, a: struct.unpack_from('>h', r, a)[0]
GB = 0x51538 + 0x13c * 3 + 0x4c                     # side 3 group 0's offset (group k at +2k)
def grp(arm, f, k=0): return h(ram(arm), GB + 2 * k + f)   # f: -24 men, 0 state, 24 target link, 36 food, 60 posture, 84+12i goods
LEAD = 0x51b66 + 0x1fd6                              # side 3 group 0's lead in rand1 (the watched record)
def at(arm, x, y): return ram(arm)[LEAD + 8] == x and ram(arm)[LEAD + 10] == y   # the lead's cell (x/y word high bytes)
def lord(arm, i, f): return h(ram(arm), 0x4e514 + 32 * i + f)   # +6 food, +8 troops_field, +14 loyalty_pressure
peace = lambda arm, s: ram(arm)[0x580a6 + 0x20 * s + 6]
def wr(arm, pc, val=None):  # watched writes by the instruction at pc (with value val)
    return sum(1 for l in open(f'{w}/{arm}.err')
               if f'pc=${pc:06x} ' in l and (val is None or l.rstrip().endswith(f'<- ${val:x}')))
send = lambda d4, pc=0x3236: lambda a: wr(a, pc, d4) == 1          # the sender stamped the arrival mode into 30(lead)
arrive = lambda d4: lambda a: wr(a, 0x14fdc, d4) >= 1              # the lead reached the target: 31(lead) := 30(lead)
def ctl_and(arm, name, sig, ctl):  # the signal holds in the arm and not in its control
    return (f'{arm}: {name}', bool(sig(arm)) and not sig(ctl))
SLOT = ['post', 'postpg', 'xfer', 'dismiss', 'dropf', 'drope']
LEADW = ['spy', 'ally', 'food', 'men', 'invent', 'equip', 'trade', 'supply']
arms = [a for a in SLOT + LEADW if os.path.exists(f'{w}/{a}.snap')]
checks = [('ctl: side 3 slot never dispatched ($6b46) nor taken by a pigeon ($45d0)', wr('ctl', 0x6b46) == 0 and wr('ctl', 0x45d0) == 0),
          ('ctlL: group 0 lead gets no new order ($3236/$3948 never write 30(lead))', wr('ctlL', 0x3236) == 0 and wr('ctlL', 0x3948) == 0)]
C = {  # name, signal; a name starting 'handler' or 'pigeon' is a hit count read from the arm alone (sides 2 and 4 call the
       # shared routines too: the slot or lead row attributes it), every other row must hold in the arm and fail in the control
 'post':   [('handler $6cc6 -> $35a0 ran', lambda a: hits(a, 0x6cc6) >= 1 and hits(a, 0x35a0) >= 1),
            ('group 0 posture 2 -> 4', lambda a: grp(a, 60) == 4)],
 'postpg': [('pigeon $4562, then handler $6cc6 -> $35a0 ran', lambda a: hits(a, 0x4562) >= 1 and hits(a, 0x6cc6) >= 1 and hits(a, 0x35a0) >= 1),
            ('group 1 posture 2 -> 4, group 0 still 2', lambda a: grp(a, 60, 1) == 4 and grp(a, 60) == 2)],
 'xfer':   [('handler $6ba8 -> $1c18 ran', lambda a: all(hits(a, x) >= 1 for x in (0x6ba8, 0x1c18))),
            ('group 1 men 17 -> 0, group 0 gains them', lambda a: grp(a, -24, 1) == 0 and grp(a, -24) >= 29)],
 'dismiss':[('handler $6cbc -> $1cc4 ran', lambda a: all(hits(a, x) >= 1 for x in (0x6cbc, 0x1cc4))),
            ('group 0 men 12 -> 0', lambda a: grp(a, -24) == 0)],
 'dropf':  [('handler $6c96 -> $39d4 ran', lambda a: all(hits(a, x) >= 1 for x in (0x6c96, 0x39d4))),
            ('group 0 food ~24500 -> < 100', lambda a: grp(a, 36) < 100)],
 'drope':  [('handler $6cda -> $39d4 ran', lambda a: all(hits(a, x) >= 1 for x in (0x6cda, 0x39d4))),
            ('group 0 boats 12 -> 0', lambda a: grp(a, 84 + 12 * 4) == 0)],
 'spy':    [('handler $6d56 -> $3154 -> $1d36 ran', lambda a: all(hits(a, x) >= 1 for x in (0x6d56, 0x3154, 0x1d36))),
            ('sender: 30(lead) := $7a', send(0x7a)), ('group 0 dismissed, 12 -> 0 men', lambda a: grp(a, -24) == 0),
            ('arrival: 31(lead) := $7a, then $3da4 sets mode $7e', lambda a: arrive(0x7a)(a) and wr(a, 0x3dca, 0x7e) == 1 and hits(a, 0x3da4) >= 1),
            ('the spy sits in the town: lead mode $7e, flag bit 7, lord 11 troops_field 0 -> 1', lambda a: ram(a)[LEAD + 31] == 0x7e and ram(a)[LEAD + 7] & 0x80 and lord(a, 11, 8) >= 1)],
 'ally':   [('handler $6d32 -> $3154 ran', lambda a: all(hits(a, x) >= 1 for x in (0x6d32, 0x3154))),
            ('sender: 30(lead) := $76', send(0x76)), ('arrival: 31(lead) := $76', arrive(0x76)),
            ('handler envoy $33b0, side 2 accepts ($3458 posts $2a -> $34a8)', lambda a: all(hits(a, x) >= 1 for x in (0x33b0, 0x3458, 0x34a8))),
            ('peace bits: side 2 bit 3 and side 3 bit 2', lambda a: peace(a, 2) & 8 and peace(a, 3) & 4)],
 'food':   [('handler $6bbe -> $3154 ran', lambda a: all(hits(a, x) >= 1 for x in (0x6bbe, 0x3154))),
            ('sender: 30(lead) := $1a', send(0x1a)), ('arrival: 31(lead) := $1a', arrive(0x1a)),
            ('handler arrival $150c0 ran', lambda a: hits(a, 0x150c0) >= 1),
            ('lord 12 town food 28 -> 0', lambda a: lord(a, 12, 6) == 0)],
 'men':    [('handler $6bea -> $3154 ran', lambda a: all(hits(a, x) >= 1 for x in (0x6bea, 0x3154))),
            # the control's lead is on its own natural get-men walk to lord 1 (48,107) and arrives there with $1c too
            # (29.8M steps in, against 16.1M here): the row that separates them is where the lead stands
            ('sender: 30(lead) := $1c', send(0x1c)),
            ('arrival at lord 12 (33,70): 31(lead) := $1c, the lead stands on (33,70)', lambda a: arrive(0x1c)(a) and at(a, 33, 70)),
            ('$15122 puts the lead in the join wait $28 ($1514c) at (33,70)', lambda a: wr(a, 0x1514c, 0x28) >= 1 and at(a, 33, 70)),
            ('group 0 target link 24 = lord 12', lambda a: (grp(a, 24) & 0xffff) == ((0x4e514 + 32 * 12 - 0x51b66) & 0xffff))],
 'invent': [('handler $6c48 -> $3154 ran', lambda a: all(hits(a, x) >= 1 for x in (0x6c48, 0x3154))),
            ('sender: 30(lead) := $22', send(0x22)), ('arrival: 31(lead) := $22', arrive(0x22)),
            ('handler arrival $5fa0 -> work order $5cde ran', lambda a: all(hits(a, x) >= 1 for x in (0x5fa0, 0x5cde)))],
 'equip':  [('handler $6c6a -> $3154 ran', lambda a: all(hits(a, x) >= 1 for x in (0x6c6a, 0x3154))),
            ('sender: 30(lead) := $6e', send(0x6e)), ('arrival: 31(lead) := $6e', arrive(0x6e)),
            ('handler arrival $61f8 ran', lambda a: hits(a, 0x61f8) >= 1)],
 'trade':  [('handler $6d12 -> $3154 ran', lambda a: all(hits(a, x) >= 1 for x in (0x6d12, 0x3154))),
            ('sender: 30(lead) := $78', send(0x78)), ('arrival: 31(lead) := $78', arrive(0x78)),
            ('handler arrival $63f4 ran', lambda a: hits(a, 0x63f4) >= 1)],
 'supply': [('handler $6d00 -> $390e ran', lambda a: all(hits(a, x) >= 1 for x in (0x6d00, 0x390e))),
            ('sender: 30(lead) := $74 ($3948)', send(0x74, 0x3948)), ('arrival: 31(lead) := $74', arrive(0x74)),
            ('$3956 drops the food and heads for the richest own lord (30(lead) := $1a at $39c2)', lambda a: hits(a, 0x3956) >= 1 and wr(a, 0x39c2, 0x1a) >= 1),
            ('group 0 food ~24500 -> < 100', lambda a: grp(a, 36) < 100)],
}
for arm in arms:
    if arm == 'postpg':   # a non-zero group: the pigeon $4562 takes the order out of the slot ($45d0 clears the type)
        checks.append((f'{arm}: side 3 slot taken by the pigeon ($45d0) once, not dispatched at once', wr(arm, 0x45d0) == 1 and wr(arm, 0x6b46) == 0))
    elif arm in SLOT:     # group 0: $6ac6 -> $6b38 at once, whose $6b46 clears the type byte of side 3's slot
        checks.append((f'{arm}: side 3 slot dispatched to $6b38 ($6b46) once', wr(arm, 0x6b46) == 1))
    ctl = 'ctl' if arm in SLOT else 'ctlL'
    for name, sig in C[arm]:
        try:
            checks.append((f'{arm}: {name}', bool(sig(arm))) if name.startswith(('handler', 'pigeon')) else ctl_and(arm, name, sig, ctl))
        except Exception as e: checks.append((f'{arm}: {name} ({e})', False))
for name, ok in checks: print('PASS' if ok else 'FAIL', name)
print(f"{sum(bool(ok) for _, ok in checks)}/{len(checks)}")
EOF
