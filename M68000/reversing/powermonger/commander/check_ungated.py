"""check_ungated.py <outdir>: the check of gate_ungated.sh. A row marked A is read from the arm alone (handler hit counts,
which sides 2 and 4 share, are attributed by the arm's slot or lead row); every other row must hold in the arm and fail in
the arm's control (same snapshot, same budget, same pokes but the order)."""
import re, struct, sys, os
from pathlib import Path
root = Path(__file__).resolve()
while not (root / 'tools/rdis.py').exists(): root = root.parent
sys.path.insert(0, str(root / 'tools'))
from disassemble import ram_from_snap

w = sys.argv[1]
RAM = {}
def ram(arm, mid=False):
    k = f'{arm}.mid' if mid else arm
    if k not in RAM: RAM[k] = ram_from_snap(f'{w}/{k}.snap')
    return RAM[k]
def hits(arm, a):   # summed over the run's hits chunks
    return sum(int(m) for m in re.findall(rf'\${a:06x}\s+(\d+)', open(f'{w}/{arm}.out').read()))
h = lambda r, a: struct.unpack_from('>h', r, a)[0]
H = lambda r, a: struct.unpack_from('>H', r, a)[0]
OBJ = 0x51b66
GB = 0x51538 + 0x13c * 3 + 0x4c                      # side 3 group 0's offset (group k at +2k)
LEAD = {0: OBJ + 0x1fd6, 1: OBJ + 0x9f6, 2: OBJ + 0xd7a}   # the watched leads (rand1 / rand1_s2)
def grp(arm, f, k=0, mid=False): return h(ram(arm, mid), GB + 2 * k + f)   # f: -24 men, 0 state, 84+12i goods, 192 prev state
def at(arm, k, x, y, mid=False): r = ram(arm, mid); return r[LEAD[k] + 8] == x and r[LEAD[k] + 10] == y
def lord(arm, i, mid=False): return ram(arm, mid)[0x4e514 + 32 * i:0x4e514 + 32 * i + 32]
peace = lambda arm, s, mid=False: ram(arm, mid)[0x580a6 + 0x20 * s + 6]
def wr(arm, pc, val=None, addr=None):  # watched writes by the instruction at pc (with value val, to address addr)
    return sum(1 for l in open(f'{w}/{arm}.err')
               if f'pc=${pc:06x} ' in l and (val is None or l.rstrip().endswith(f'<- ${val:x}'))
               and (addr is None or f'${addr:08x} ' in l))
def roster_boats(arm):   # men of side 3 group 2 (lead + roster) holding a boat: byte 33 = $a
    r = ram(arm); ms = [H(r, GB + 4 - 12)]; o = H(r, GB + 4 - 36)
    while o and len(ms) < 200: ms.append(o); o = H(r, OBJ + o + 26)
    return sum(1 for m in ms if r[OBJ + m + 33] == 0xa)
send = lambda d4, pc=0x3236: lambda a: wr(a, pc, d4) == 1          # the sender stamped the arrival mode into 30(lead)
arrive = lambda d4: lambda a: wr(a, 0x14fdc, d4) >= 1              # the lead reached the target: 31(lead) := 30(lead)
A = True   # arm-only row

CTL = {'goto': 'ctlL', 'home': 'ctlL', 'ally': 'ctlL', 'allyng': 'ally', 'allyp': 'ctlL', 'invent': 'ctlL1',
       'allyyes': 'ctlP', 'allyno': 'ctlP', 'equip': 'ctlE', 'inventT': 'ctlT'}
C = {
 'goto':   [('handler $6b8e -> $3888 ran', A, lambda a: hits(a, 0x6b8e) >= 1 and hits(a, 0x3888) >= 1),
            ('sender $3888: 30(lead) := $1e ($38c0)', 0, send(0x1e, 0x38c0)),
            ('arrival: 31(lead) := $1e, then $1515c -> $35f4 camps ($371a writes $6868)', 0,
             lambda a: arrive(0x1e)(a) and hits(a, 0x1515c) >= 1 and wr(a, 0x371a, 0x6868) >= 1),
            ('group 0 in camp (state 6) with its lead on (33,72)', 0, lambda a: grp(a, 0) == 6 and at(a, 0, 33, 72))],
 'home':   [('handler $6c16 -> $3c08 ran', A, lambda a: hits(a, 0x6c16) == 1 and hits(a, 0x3c08) >= 1),
            ('$3c08: 30(lead) := $4c ($3c6a), 31 := $10 ($3cd0), target 20/22 = the home Tower cell (33,70)', 0,
             lambda a: wr(a, 0x3c6a, 0x4c) == 1 and wr(a, 0x3cd0, 0x10) == 1 and ram(a)[LEAD[0] + 20] == 33 and ram(a)[LEAD[0] + 22] == 70),
            ('arrival: 31(lead) := $4c, $16176 ran and wrote $8a8a ($161a4)', 0,
             lambda a: arrive(0x4c)(a) and hits(a, 0x16176) >= 1 and wr(a, 0x161a4, 0x8a8a) == 1),
            ('group 0 in camp (state 6) with its lead on its home cell (33,70)', 0, lambda a: grp(a, 0) == 6 and at(a, 0, 33, 70))],
 'ally':   [('handler $6d32 -> $3154 ran', A, lambda a: hits(a, 0x6d32) >= 1 and hits(a, 0x3154) >= 1),
            ('sender: 30(lead) := $76', 0, send(0x76)), ('arrival: 31(lead) := $76', 0, arrive(0x76)),
            ('envoy $33b0, side 2 accepts ($3458 posts $2a -> $6dea -> $34a8)', 0,
             lambda a: all(hits(a, x) == 1 for x in (0x33b0, 0x3458, 0x6dea, 0x34a8))),
            ('peace bits at mid: side 2 bit 3 and side 3 bit 2; the 12 boats paid', 0,
             lambda a: peace(a, 2, 1) & 8 and peace(a, 3, 1) & 4 and grp(a, 84 + 48, mid=True) == 0)],
 'allyng': [('group 0 starts with no goods (poke): $33b0 had nothing to take', A, lambda a: 'w 519bc 0000000c' in open(f'{w}/{a}.repl').read()),
            ('handler $6d32 -> $3154 ran; sender 30(lead) := $76; arrival 31(lead) := $76', A,
             lambda a: hits(a, 0x6d32) >= 1 and send(0x76)(a) and arrive(0x76)(a)),
            ('handler envoy $33b0 ran once', A, lambda a: hits(a, 0x33b0) == 1 and hits(a, 0x15754) == 1),
            ('refused: no $3458, no $34a8, peace bits at mid side 2 $04, side 3 $08 (the goods twin, ally, accepts)', 0,
             lambda a: hits(a, 0x3458) == 0 and hits(a, 0x34a8) == 0 and peace(a, 2, 1) == 4 and peace(a, 3, 1) == 8),
            ('no refusal notice: $cada 0 (the proposer is not the local side)', A, lambda a: hits(a, 0xcada) == 0)],
 'allyp':  [('handler $6d32 -> $3154 ran', A, lambda a: hits(a, 0x6d32) >= 1 and hits(a, 0x3154) >= 1),
            ('sender: 30(lead) := $76', 0, send(0x76)), ('arrival at lord 9 (15,92): 31(lead) := $76', 0, arrive(0x76)),
            ('$33b0 -> $c706: panel $1a open at mid ($7a3c = $1a), $5809e = $400 (side 3 group 0), group prev state $e', 0,
             lambda a: hits(a, 0xc706) == 1 and H(ram(a, 1), 0x7a3c) == 0x1a and H(ram(a, 1), 0x5809e) == 0x400 and grp(a, 192, mid=True) == 0xe),
            ('no verdict for side 1 (slot state 2): no $3458, no $6dea; side 1 peace $02 at the end', A,
             lambda a: hits(a, 0x3458) == 0 and hits(a, 0x6dea) == 0 and peace(a, 1) == 2),
            ('bug: $c706 clobbers A0 (8 after it), so $33b0 judges for "side 0": $34a8 sets side 0 bit 3, side 3 bit 0', 0,
             lambda a: hits(a, 0x34a8) == 1 and peace(a, 0) == 8 and peace(a, 3) == 9)],
 'allyyes':[('the click posts $2a, param $400, into side 1\'s slot ($79f0, $79f6)', 0,
             lambda a: wr(a, 0x79f0, 0x2a, 0x5801d) == 1 and wr(a, 0x79f6, 0x400, 0x5801e) == 1),
            ('$6dea -> $34a8 -> $c9f8 (the "alliance forged" notice) ran once each', 0,
             lambda a: all(hits(a, x) == 1 for x in (0x6dea, 0x34a8, 0xc9f8))),
            ('peace bits: side 1 $02 -> $0a (bit 3), side 3 $09 -> $0b (bit 1)', 0, lambda a: peace(a, 1) == 0xa and peace(a, 3) == 0xb)],
 'allyno': [('the click posts $32, param $400, into side 1\'s slot ($7a12, $7a18)', 0,
             lambda a: wr(a, 0x7a12, 0x32, 0x5801d) == 1 and wr(a, 0x7a18, 0x400, 0x5801e) == 1),
            ('$6e56 ran once, panel closed (slot 0 word 0 = 0)', 0, lambda a: hits(a, 0x6e56) == 1 and H(ram(a), 0x7a36) == 0),
            ('no alliance, no notice: $34a8, $c9f8, $cada 0; peace side 1 $02, side 3 $09', A,
             lambda a: all(hits(a, x) == 0 for x in (0x34a8, 0xc9f8, 0xcada)) and peace(a, 1) == 2 and peace(a, 3) == 9)],
 'invent': [('pigeon $4562, then handler $6c48 -> $3154 ran', A, lambda a: all(hits(a, x) >= 1 for x in (0x4562, 0x6c48, 0x3154))),
            ('sender: 30(lead1) := $22', 0, send(0x22)), ('arrival: 31(lead1) := $22', 0, arrive(0x22)),
            ('$151a8 -> $5fa0 -> $5cde accepted at a WorkShop lord: lead mode $92 ($5ff6)', 0,
             lambda a: hits(a, 0x151a8) >= 1 and hits(a, 0x5fa0) >= 1 and wr(a, 0x5ff6, 0x92) == 1),
            ('lord 5 work order at mid: gather kind $e (Catapult), throttle $328f = word8 $128b + 4 + $2000', 0,
             lambda a: H(lord(a, 5, 1), 12) == 0xe and H(lord(a, 5, 1), 16) == 0x328f),
            ('no invention within the budget: lord 5 goods all 0', A,
             lambda a: not any(lord(a, 5)[24:32]))],
 'inventT':[('pigeon $4562, then handler $6c48 -> $3154 ran', A, lambda a: all(hits(a, x) >= 1 for x in (0x4562, 0x6c48, 0x3154))),
            ('sender: 30(lead2) := $22', 0, send(0x22)), ('arrival: 31(lead2) := $22', 0, arrive(0x22)),
            ('$5fa0 -> $5cde accepted: lead mode $92 ($5ff6); lord 3 gather kind $a (Boat: posture 4, flag bit 2)', 0,
             lambda a: wr(a, 0x5ff6, 0x92) == 1 and H(lord(a, 3), 12) == 0xa),
            ('the invention appears: lord 3 boats 13 -> more ($60dc credits at $6120)', 0,
             lambda a: lord(a, 3)[24 + 4] > 13 and hits(a, 0x6120) >= 1)],
 'equip':  [('pigeon $4562, then handler $6c6a -> $3154 ran', A, lambda a: all(hits(a, x) >= 1 for x in (0x4562, 0x6c6a, 0x3154))),
            ('sender: 30(lead2) := $6e', 0, send(0x6e)), ('arrival: 31(lead2) := $6e', 0, arrive(0x6e)),
            ('$15740 -> $61f8 -> lord arm $6306 -> $6352 ran', A, lambda a: all(hits(a, x) >= 1 for x in (0x15740, 0x61f8, 0x6306, 0x6352))),
            ('lord 3 boats 13 -> 10 (13 >> 2 at posture 4)', 0, lambda a: lord(a, 3)[24 + 4] == 10),
            ('the 3 + 12 carried boats go to the men: carried 12 -> 0, men holding a boat 1 -> 16', 0,
             lambda a: grp(a, 84 + 48, 2) == 0 and roster_boats(a) == 16)],
}
checks = []
if os.path.exists(f'{w}/ctlL.err'):
    checks.append(('ctlL: group 0 lead gets no order ($3236, $3948, $38c0, $3c6a never write 30(lead))',
                   all(wr('ctlL', pc) == 0 for pc in (0x3236, 0x3948, 0x38c0, 0x3c6a))))
if os.path.exists(f'{w}/ctlL1.err'):
    checks.append(('ctlL1: group 1 lead gets no order ($3236, $5ff6 never write it; no $4562 launch for it)',
                   wr('ctlL1', 0x3236) == 0 and wr('ctlL1', 0x5ff6) == 0))
for c in ('ctlE', 'ctlT'):
    if os.path.exists(f'{w}/{c}.err'):   # both inherit the get-food pigeon already in flight in rand1_s2 ($1a), as their arms do
        checks.append((f'{c}: no pigeon launched ($4562 0); lead 2 gets only the inherited get-food $1a', hits(c, 0x4562) == 0
                       and wr(c, 0x3236) == 1 and wr(c, 0x3236, 0x1a) == 1))
if os.path.exists(f'{w}/ctlP.err'):
    checks.append(('ctlP: nothing posts $2a or $32 into side 1\'s slot ($5801d); the panel stays open ($7a3c = $1a)',
                   not any('$0005801d ' in l and l.rstrip().endswith(('<- $2a', '<- $32')) for l in open(f'{w}/ctlP.err'))
                   and H(ram('ctlP'), 0x7a3c) == 0x1a))
for arm, rows in C.items():
    if not os.path.exists(f'{w}/{arm}.snap'): continue
    ctl = CTL[arm]
    for name, alone, sig in rows:
        try:
            ok = bool(sig(arm)) if alone else (bool(sig(arm)) and not sig(ctl))
        except Exception as e:
            name, ok = f'{name} ({e!r})', False
        checks.append((f'{arm}: {name}' + ('' if alone else f' [not in {ctl}]'), ok))
for name, ok in checks: print('PASS' if ok else 'FAIL', name)
print(f"{sum(bool(ok) for _, ok in checks)}/{len(checks)}")
