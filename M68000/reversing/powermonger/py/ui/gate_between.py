"""pm147 panels: gate for the briefing ("Between Pages a-b / How many <word> in this land?") dialog formatters of template $b510:
  $b476  run 1 '@@@@@' (page range text, written to A4, A1 advanced by its length)
  $b4d0  run 2 '@@@@@@' (the question noun: A5 -> $b4e6+4+byte[$b4e6+$57ff8])
Model from the code read:  k = ((P - $5dc) / $96) >> 2 with P = word $5809c;  D3 = (rand & 3) + 2 (rand $12c9a is an LCG on the long $2df84, poked per case; D3 is read back from the callcap's own regdelta);
  text = "<max(k-D3,-1)+2>-<k-D3+7>".   Real routine by callcap on P = n*$96+$672 for n = 0..143 (the 144 lands) and P poked off-grid too.
    cd M68000 && uv run python reversing/powermonger/py/ui/gate_between.py"""
import os, sys
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/ui'))
from uilib import *
SNAP = ROOT / 'scratchpad/pm123/win/m1_s0.snap'
BUF = 0x7bac
base = ram_of(SNAP)
def model(P, d3):
    k = (((P - 0x5dc) & 0xffff) // 0x96) >> 2
    return f'{max(k - d3, -1) + 2}-{k - d3 + 7}'
Ps = [n * 0x96 + 0x672 for n in range(144)] + [0x5dc + 0x96 * 7, 0x5dc + 0x96 * 400, 0x672 + 3]
import random
rnd = random.Random(147)
cmds = []
for P in Ps:
    cmds += [f'w 2df84 {rnd.getrandbits(32):08x}', f'w 5809c {P:04x}{(base[0x5809e] << 8) | base[0x5809f]:04x}', f'callcap b476 5000 A4={BUF:x} A1={BUF:x}']
for v in range(4):
    cmds += [f'w 57ff8 {v:04x}{(base[0x57ffa] << 8) | base[0x57ffb]:04x}', 'callcap b4d0 5000']
ccs = parse_callcaps(repl(str(SNAP), cmds))
assert len(ccs) == len(Ps) + 4, len(ccs)
ok = tot = 0; bad = []; d3s = set()
for P, cc in zip(Ps, ccs[:len(Ps)]):
    tot += 1
    d3 = cc['regs']['D3'][1] & 0xffff; d3s.add(d3)
    ab = after_ram(base, cc)
    n = cc['regs']['A4'][1] - BUF
    txt = bytes(ab[BUF:BUF + n]).decode('latin1')
    adv = cc['regs']['A1'][1] - BUF
    if txt == model(P, d3) and adv == n and cc['returned'] and 2 <= d3 <= 5: ok += 1
    else: bad.append((hex(P), d3, txt, model(P, d3)))
print(f'$b476 page range: {ok}/{tot}  (D3 values seen {sorted(d3s)})')
for b in bad[:5]: print('MISMATCH', b)
ok2 = 0
for v, cc in zip(range(4), ccs[len(Ps):]):
    a5 = cc['regs']['A5'][1]; s = bytes(base[a5:a5 + 8]).split(b'\0')[0].decode()
    want = 0xb4e6 + 4 + base[0xb4e6 + v]
    ok2 += (a5 == want)
    print(f'  $57ff8={v}: A5=${a5:x} -> {s!r}')
print(f'$b4d0 noun: {ok2}/4')
