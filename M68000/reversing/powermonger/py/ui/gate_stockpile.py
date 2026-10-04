"""pm147 panels: differential gate for the stockpile (goods pile, byte6 $2c) panel opener $9656 with its formatters
$9684 (food line) and $96ae (one non-zero good per call).  Model from the code read; real routine by `callcap $9656`
on the pile record with the food word (10(A3)) and the eight goods words (12(A3)..26(A3)) poked to test values.
    cd M68000 && uv run python reversing/powermonger/py/ui/gate_stockpile.py [snap ...]
Prints matched/total and the first mismatches.  Root: env M68000_ROOT or four levels above this file."""
import os, sys, random
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/ui')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py'))
from uilib import *
from census import walk

ITEMS = ['Pike', 'Sword', 'Bow', 'Plough', 'Boat', 'Pot', 'Catapult', 'Cannon']
RUNS = [13, 13, 13, 13, 13, 13, 13, 12, 11]          # '@' run widths of template $9712, rows 2..10

def s16(v): return v - 65536 if v >= 32768 else v

def model(food, goods):
    """-> the nine interior rows (cells 1..18) of the panel, rows 2..10, as $a91a builds them."""
    out = []
    out.append(f'{s16(food)} food' if food else '')
    for n, name in zip(goods, ITEMS):
        if n:
            out.append(f'{s16(n)} {name}' + ('s' if s16(n) > 1 else ' '))
    out += [''] * (9 - len(out))
    rows = []
    TAIL = [' ' * 4] * 7 + [' ' * 5, ' .... ']       # template bytes after each '@' run, before the $f0 (row 10: ' ', ornament, ' ')
    for t, w, tail in zip(out, RUNS, TAIL):
        # formatter writes straight into the grid (A4) and advances the template cursor (A1) by its length: no truncation at the run end,
        # an over-long text eats the template's literal tail; unused '@' cells are counted (D6) and emitted as spaces at the $f0 cell.
        rows.append(' ' + t + (('@' * w) + tail)[len(t):].replace('@', '') + ' ' * max(0, w - len(t)))
    return rows

def pokes(base, rec, food, goods):
    ws = [food] + goods + [(base[rec + 28] << 8) | base[rec + 29]]      # words at +10, +12 .. +26, and +28 kept
    return [f'w {rec + 10 + 4 * i:x} {ws[2 * i]:04x}{ws[2 * i + 1]:04x}' for i in range(5)]

def main(snaps):
    rnd = random.Random(147)
    vals = [0, 0, 0, 1, 1, 2, 3, 10, 99, 300, 5450, 40000]
    tot = ok = 0; bad = []
    for snap in snaps:
        base = ram_of(snap); recs, torn = walk(base)
        piles = [o for o, cx, cy, r in recs if r[6] == 0x2c]
        cases = []
        for o in piles:
            w = lambda a: (base[a] << 8) | base[a + 1]
            cases.append((o, w(o + 10), [w(o + 12 + 2 * i) for i in range(8)]))      # natural
            for _ in range(10):
                cases.append((o, rnd.choice(vals), [rnd.choice(vals) for _ in range(8)]))
        cmds = []
        for o, f, g in cases:
            cmds += pokes(base, o, f, g) + [f'callcap 9656 30000 A3={o:x}']
        out = repl(snap, cmds)
        ccs = parse_callcaps(out)
        assert len(ccs) == len(cases), (len(ccs), len(cases))
        for (o, f, g), cc in zip(cases, ccs):
            rows = panel_text(base, cc) if cc['mem'] else None
            tot += 1
            if not rows or not cc['returned']:
                bad.append((snap, hex(o), 'no panel', cc['hdr'])); continue
            got = [r[1:19] for r in rows[2:11]]
            want = model(f, g)
            # gate also the frame: header row and the empty tail of every row must be untouched
            if got == want and rows[1].strip(' .') == 'Stockpile of:' and all(r[0] == '.' and r[19] == '.' for r in rows):
                ok += 1
            else:
                bad.append((snap, hex(o), f, g, got, want))
    print(f'stockpile panel gate: {ok}/{tot}')
    for b in bad[:6]: print('MISMATCH', b)

if __name__ == '__main__':
    main(sys.argv[1:] or [str(ROOT / 'scratchpad/pm143/run/p0k0_s4.snap')])
