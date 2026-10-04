"""pm147 panels: gate for the mine panel opener $a5d8 (template $a658, formatter table $a5f4 -> $a5fa $a620 $a63a).
Model from the code read: the mine record's word 14 is an offset into the lord table $4e514; with L = that lord record
  run 0  $a5fa  townname[$a128] indexed by L byte 1 (kind 1..6: Village Hamlet Town City Capital Base)
  run 1  $a620  _getname $a9ce seeded with word 4 of L (the lord's cell)
  run 2  $a63a  item name $a242[word 12 of L] (word 12 holds the item code 2..$10, so the weapon the metal makes), 's' is a literal in the template.
Real routine by `callcap $a5d8` on every byte6 $1e record of the given snapshots (default: the pm143 run set + m1_s0).
    cd M68000 && uv run python reversing/powermonger/py/ui/gate_mine.py [snap ...]"""
import os, sys, glob
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/ui')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py'))
from uilib import *
from census import walk
import gate_getname as G

def cstr(R, x):
    o = bytearray()
    while R[x]: o.append(R[x]); x += 1
    return o.decode('latin1')

def model(R, a):
    w = lambda x: (R[x] << 8) | R[x + 1]
    L = 0x4e514 + w(a + 14)
    kind = cstr(R, 0xa128 + 12 + w(0xa128 + 2 * (R[L + 1] - 1)))
    town = G.model_from(R, w(L + 4))
    item = cstr(R, 0xa242 + 20 + w(0xa242 + w(L + 12)))
    return kind, town, item

def main(snaps):
    tot = ok = 0; bad = []; seen = set()
    for snap in snaps:
        base = ram_of(snap); recs, torn = walk(base)
        mines = [o for o, cx, cy, r in recs if r[6] == 0x1e]
        mines = [o for o in mines if base[0x4e514 + ((base[o + 14] << 8) | base[o + 15]) + 1] in range(1, 7)]
        if not mines: continue
        w0 = lambda x: (base[x] << 8) | base[x + 1]
        cases = []                                   # (mine, kind, town-seed word, item offset): the natural state, then every item with a rotating kind and seed
        for o in mines:
            L = 0x4e514 + w0(o + 14)
            cases.append((o, base[L + 1], w0(L + 4), w0(L + 12)))
            for j in range(8): cases.append((o, 1 + (j + o) % 6, (0x1234 * (j + 1) + o) & 0xffff, 2 * (j + 1)))
        cmds = []
        for o, kind, seed, itm in cases:
            L = 0x4e514 + w0(o + 14)
            cmds += [f'w {L:x} {base[L]:02x}{kind:02x}{w0(L + 2):04x}', f'w {L + 4:x} {seed:04x}{w0(L + 6):04x}', f'w {L + 12:x} {itm:04x}{w0(L + 14):04x}',
                     f'callcap a5d8 60000 A3={o:x}']
        ccs = parse_callcaps(repl(snap, cmds))
        for (o, kind, seed, itm), cc in zip(cases, ccs):
            tot += 1
            rows = panel_text(base, cc) if cc['mem'] else None
            if not rows: bad.append((snap, hex(o), 'no panel')); continue
            R = after_ram(base, cc)                  # the model reads the poked lord record, exactly as the routine does
            L = 0x4e514 + w0(o + 14)
            R = bytearray(base); R[L + 1] = kind; R[L + 4:L + 6] = seed.to_bytes(2, 'big'); R[L + 12:L + 14] = itm.to_bytes(2, 'big')
            k, t, i = model(R, o); seen.add((k, i))
            # unused '@' cells of a run are not emitted where they stand but at the row's $f0 (D6 spaces), so the text closes up
            got = (rows[2][2:27].rstrip(), rows[3][2:27].rstrip(), rows[4][2:27].rstrip())
            want = (f'{k} of {t} it', 'produces metal that ....', f'makes the {i}s')
            r2 = rows[1][2:26].strip() == 'This Mine belongs to the' and all(r[0] == '.' and r[27] == '.' for r in rows)
            if got == want and r2: ok += 1
            else: bad.append((Path(snap).name, hex(o), got, want))
    print(f'mine panel gate: {ok}/{tot}  kinds/items seen: {len(seen)} distinct (kind, item)')
    for b in bad[:5]: print('MISMATCH', b)

if __name__ == '__main__':
    snaps = sys.argv[1:] or sorted(glob.glob(str(ROOT / 'scratchpad/pm143/run/*_s4.snap'))) + [str(ROOT / 'scratchpad/pm123/win/m1_s0.snap')]
    main(snaps)
