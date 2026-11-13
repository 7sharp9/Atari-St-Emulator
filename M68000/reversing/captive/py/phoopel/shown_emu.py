"""Emulator gate for the clipboard number: run federation's $12d4e (entered with D0 = item word, A0 = $12db9, and
32(A6) = base number poked) under stserver, stop after the decimal conversion $727a returns ($12d78), read the five
digit bytes at 15114(A6) and compare with shown.shown(). Labelled pokes: 32(A6) only. Then, for the Phoopel key,
run the whole clipboard reader $12dc2 on a poked item record (type $5d, word 34080) and render the screen.
Usage: shown_emu.py <snap> <n_random> <out.png>"""
import os, sys, random
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/ai')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import R, StServer, snappath, A6  # noqa: E402
from shown import shown  # noqa: E402

snap, n, png = sys.argv[1], int(sys.argv[2]), sys.argv[3]
s = StServer(R)
s('load', snapshot=snappath(snap))
base = s('fork')['id']

def digits(word, d0):
    s('restore', id=base); s.sp = None
    s('poke', addr=A6 + 32, width=2, value=d0)
    s.call(0x12d4e, stops=[0x12d78], d0=word, a0=0x12db9)
    pc = s.reg('pc')
    raw = s.read(A6 + 15114, 5)
    txt = ''.join(' ' if b == 1 else chr(b) for b in raw)
    return pc, raw, txt

rng = random.Random(1)
cases = [(34080, 13)] + [(rng.randrange(65536), rng.randrange(1100)) for _ in range(n)]
ok = 0
for i, (word, d0) in enumerate(cases):
    pc, raw, txt = digits(word, d0)
    want = shown(word, d0)
    good = pc == 0x12d78 and txt.strip() != '' and int(txt.replace(' ', '0')) == want
    ok += good
    if i < 3 or not good:
        print(f'word {word} d0 {d0}: stop ${pc:x} bytes {raw.hex()} text {txt!r} model {want:05d} {"ok" if good else "MISS"}')
print(f'$12d4e digits == model: {ok}/{len(cases)}')
# control: the same calls with 32(A6) left at the snapshot's own value (base 0) disagree with the d0 != 0 model
bad = 0
for word, d0 in cases[1:51]:
    s('restore', id=base); s.sp = None
    s.call(0x12d4e, stops=[0x12d78], d0=word, a0=0x12db9)
    txt = ''.join(' ' if b == 1 else chr(b) for b in s.read(A6 + 15114, 5))
    bad += int(txt.replace(' ', '0')) == shown(word, d0) and d0 != 0
print(f'control (32(A6) not poked): model with the case d0 matches {bad}/50')

# whole reader on a poked record
s('restore', id=base); s.sp = None
rec = s.reg('a7') - 0x400
s('poke', addr=A6 + 32, width=2, value=13)
s('poke', addr=rec, width=4, value=(0x5d << 16) | 34080)
r = s.call(0x12dc2, max_steps=3000000, a0=rec)
print('reader $12dc2 returned', r.get('reason'), 'digits', s.read(A6 + 15114, 5))
print(s('render', path=png))
s.close()
