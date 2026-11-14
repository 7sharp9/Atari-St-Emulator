"""Gate: every call of the tile filler $26b78 from a REPL `bp` run (see tile_bp.txt) gets its vertices from the
vertex rows at A6 and its colour index A0 from the type-word array at A3-2.  Usage: python virus_tiles_check.py <tile_bp.txt> [--break]"""
import re, sys
txt = open(sys.argv[1]).read().split('\n')
# memory dumps: the two lines of hex bytes printed after the first breakpoint
hexlines = [l for l in txt if re.fullmatch(r'([0-9a-f]{2} )+[0-9a-f]{2}', l.strip())]
vert = bytes.fromhex(hexlines[0].replace(' ', '')); typ = bytes.fromhex(hexlines[1].replace(' ', ''))
W = lambda m, off: int.from_bytes(m[off:off+2], 'big')
calls = []; cur = {}
for l in txt:
    for k, v in re.findall(r'([DA]\d):([0-9a-f]{8})', l): cur[k] = int(v, 16)
    if l.startswith('PC: 00026b78'):
        calls.append(dict(cur))
calls = calls[0::2][:132]   # each stop printed registers twice (bp report and the `r` after it); 11 rows x 12 tiles
ok_c = ok_v = n = 0
sh = 2 if '--break' in sys.argv else 0
for c in calls:
    a6 = c['A6']; a3 = c['A3']
    n += 1
    ok_c += (c['A0'] & 0xffff) == W(typ, a3 - 2 - 0x275c4 + sh)
    ex = [W(vert, a6 - 0x27354 + o) for o in (0, 2, 4, 6, 52, 54, 56, 58)]
    got = [c[f'D{i}'] & 0xffff for i in range(8)]
    ok_v += ex == got
print(f'tile calls {n}: colour index == type word {ok_c}/{n};  8 vertex words == rows at A6 and A6+52: {ok_v}/{n}')
