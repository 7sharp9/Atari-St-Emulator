"""gate_observe.py [snap ...]: observe.py against the existing scripts for every field they share, and the
$57fba totals against the $d322/$3e06 rule. Prints per snapshot matched/total per source and a grand total.
  py/side_dump.py  lords (idx, cell, food, men at home, loyalty) per side; groups (men, state, posture, word 4) per side
  py/sides.py      clock, ratio, local side, selected group, $57fba, lords (side, cell, food, field, loyalty, goods), slots
  py/group.py      the selected group (state, men, food, posture, carrying, lead cell); with `settl` the settlements
                   (owner, category, kind, cell, lord) of records 0..199
Run from M68000/ with `uv run python`. Data dir $CMD_WORK (default scratchpad/cmd1)/observe_gate."""
import os, re, subprocess, sys
from pathlib import Path
ROOT = next(d for d in Path(__file__).resolve().parents if (d / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(Path(__file__).resolve().parent))
from observe import observe, load
PY = ROOT / 'reversing/powermonger/py'
WORK = ROOT / os.environ.get('CMD_WORK', 'scratchpad/cmd1') / 'observe_gate'
DEFAULT = ['scratchpad/pm142/rand1.snap'] + [f'scratchpad/pm148/arms/long/{n}.snap' for n in
           ('X10G_k25_c5', 'X10G_k40_c20', 'X10G_k44_c10', 'X10G_k143_c40', 'W5G_k80_c10', 'W5G_k108_c20')]


def run(script, *args):
    return subprocess.run([sys.executable, str(PY / script), *map(str, args)], capture_output=True, text=True, check=True).stdout


def gate(snap):
    WORK.mkdir(parents=True, exist_ok=True)
    R = load(snap); ram = WORK / (Path(snap).stem + '.ram'); ram.write_bytes(R)
    o = observe(R); S = o['sides']
    c = {}                                         # source -> [ok, total]
    bad = []
    def chk(src, name, a, b):
        t = c.setdefault(src, [0, 0]); t[1] += 1
        if a == b: t[0] += 1
        else: bad.append((src, name, a, b))
    lord_by_idx = {l['idx']: l for s in S.values() for l in s['lords']}
    # ---- side_dump.py ----
    for line in run('side_dump.py', snap).splitlines():
        m = re.match(r'side (\d) lords .*?: (.*)', line)
        if m:
            s = int(m.group(1)); got = eval(m.group(2))
            mine = [(l['idx'], tuple(l['cell']), l['food'], l['men_home'], l['loyalty']) for l in S.get(s, {}).get('lords', [])]
            chk('side_dump', f'side {s} lord count', len(mine), len(got))
            for a, b in zip(mine, got):
                for f, x, y in zip(('idx', 'cell', 'food', 'home', 'loyalty'), a, b): chk('side_dump', f'lord {a[0]} {f}', x, y)
        m = re.match(r'side (\d) groups .*?: (.*)', line)
        if m:
            s = int(m.group(1)); got = eval(m.group(2))
            for g, b in zip(S[s]['groups'], got):
                for f, x, y in zip(('men', 'state', 'posture', 'w4'), (g['men'], g['state'], g['posture'], g['raw_w4']), b):
                    chk('side_dump', f'side {s} group {g["k"]} {f}', x, y)
    # ---- sides.py ----
    out = run('sides.py', ram)
    m = re.search(r'local side (\d+)\s+ratio \$57fce=(\d+).*?\$57fd2=0x([0-9a-f]+).*tick \$2df72=(\d+)', out)
    chk('sides', 'local side', o['local_side'], int(m.group(1))); chk('sides', 'ratio', o['ratio'], int(m.group(2)))
    chk('sides', 'selected', o['selected_group'], int(m.group(3), 16)); chk('sides', 'clock', o['clock'], int(m.group(4)))
    tot = eval(re.search(r'per side: (\[.*\])', out).group(1))
    for s in range(1, 5): chk('sides', f'57fba {s}', S[s]['totals']['raw_57fba'], list(tot[s]))
    for m in re.finditer(r'leader\s+(\d+) side (\d+) cell \(\s*(\d+),\s*(\d+)\) food\s+(\d+) field\s+(\d+) loy\s+(-?\d+) goods (\[.*\])', out):
        i, side, x, y, food, field, loy = map(int, m.groups()[:7]); goods = eval(m.group(8))
        if side == 0: continue                     # observe skips side-0 (empty) slots, E1
        l = lord_by_idx.get(i)
        chk('sides', f'lord {i} present', l is not None, True)
        if l:
            for f, a, b in (('side', l['side'], side), ('cell', l['cell'], [x, y]), ('food', l['food'], food), ('field', l['men_home'], field),
                            ('loy', l['loyalty'], loy), ('goods', list(l['goods'].values()), goods)): chk('sides', f'lord {i} {f}', a, b)
    for m in re.finditer(r'cmd slot (\d) (\[.*\])', out):
        s = int(m.group(1))
        if 1 <= s <= 4: chk('sides', f'slot {s}', list(bytes.fromhex(S[s]['slot']['raw'])), eval(m.group(2)))
    # ---- group.py settl ----
    out = run('group.py', ram, 'settl')
    sel = o['selected_group']; q, r = divmod(sel - 0x4c, 0x13c)
    if sel and 1 <= q <= 4:
        g = S[q]['groups'][r // 2]
        m = re.search(r'state (\d+) men\(-24\) (\d+) .*?food\(36\) (\d+) posture\(60\) (\d+) carrying\(84\) (\[.*?\])', out)
        for f, a, b in (('state', g['state'], int(m.group(1))), ('men', g['men'], int(m.group(2))), ('food', g['food'], int(m.group(3))),
                        ('posture', g['posture'], int(m.group(4))), ('carrying', list(g['carrying'].values()), eval(m.group(5)))):
            chk('group', f'selected {f}', a, b)
        m = re.search(r' lead 0x([0-9a-f]+) cell \((-?\d+),(-?\d+)\)', out)
        chk('group', 'lead', g['lead'], int(m.group(1), 16)); chk('group', 'lead cell', g['lead_obj']['cell'], [int(m.group(2)), int(m.group(3))])
    sett_by_idx = {x['idx']: x for s in S.values() for x in s['settlements']}
    for x in o['other_settlements']: sett_by_idx[x['idx']] = x
    for m in re.finditer(r'settl\s+(\d+) @0x[0-9a-f]+ owner (\d+) cat 0x([0-9a-f]+) kind (\d+) cell \((\d+), (\d+)\) lord (\d+)', out):
        i, own, cat, kind, x, y, lo = int(m.group(1)), int(m.group(2)), int(m.group(3), 16), int(m.group(4)), int(m.group(5)), int(m.group(6)), int(m.group(7))
        if own == 0: continue                      # E3: owner 0 = free slot, observe skips it
        st = sett_by_idx.get(i)
        chk('group', f'settl {i} present', st is not None, True)
        if st:
            for f, a, b in (('owner', st['owner'], own), ('cat', st['category'], cat), ('kind', st['kind'], kind), ('cell', st['cell'], [x, y]),
                            ('lord', st['raw_leader_off'] // 32, lo)): chk('group', f'settl {i} {f}', a, b)
    # ---- $57fba rule (S-tot + $d366): word0 = lords' men at home + group men, word2 = food of lords with men at home ----
    for s in range(1, 5):
        t = S[s]['totals']
        chk('57fba-rule', f'side {s} word0', t['raw_57fba'][0], t['men_home'] + t['group_men'])
        chk('57fba-rule', f'side {s} word2', t['raw_57fba'][1], t['lord_food_manned'])
    return c, bad


if __name__ == '__main__':
    snaps = sys.argv[1:] or DEFAULT
    os.chdir(ROOT)
    grand = {}
    for snap in snaps:
        c, bad = gate(snap)
        print(Path(snap).stem, '  '.join(f'{k} {v[0]}/{v[1]}' for k, v in c.items()))
        for b in bad[:8]: print('   MISMATCH', b)
        for k, v in c.items(): g = grand.setdefault(k, [0, 0]); g[0] += v[0]; g[1] += v[1]
    print('TOTAL', '  '.join(f'{k} {v[0]}/{v[1]}' for k, v in grand.items()))
