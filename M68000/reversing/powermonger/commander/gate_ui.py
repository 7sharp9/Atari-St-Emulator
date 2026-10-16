"""gate_ui.py [snap ...]: observe.py's JSON against the game's own panels, built by the real routines under callcap
(py/ui/uilib.py renders the panel grid the routine writes; strategy.md "The game's own text", "How a panel opens").
  groups:      captain panel $9036 (A3 = side base + 2k) for every live group: "Job:" = state name, the aggression
               line's posture half, "Food:" = food 112(), "Troops:" = men 52()
  lords+settl: house panel $95f6 ($2df96 = 1, A3 = a $4f916 building of category 2 or $10, one per lord): "Kingdom:" =
               the side name of the building's owner byte, "Food:" = lord food +6, "Men: N who are W" = lord +8 and the
               loyalty word of +14, "Stock" = lord goods +24..31
Run from M68000/ with `uv run python`."""
import re, sys
from pathlib import Path
ROOT = next(d for d in Path(__file__).resolve().parents if (d / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/ui'))
from observe import observe, load
from uilib import repl, parse_callcaps, panel_text
from gate_panels import stock_of

DEFAULT = ['scratchpad/pm142/rand1.snap', 'scratchpad/pm148/arms/long/X10G_k25_c5.snap', 'scratchpad/pm148/arms/long/W5G_k80_c10.snap']


def cstr(R, a):
    o = bytearray()
    while R[a]: o.append(R[a]); a += 1
    return o.decode('latin1')


def field(row):
    return re.sub(r'\s+', ' ', re.sub(r'^\. [A-Za-z ]+:\s*', '', row)[:-1].rstrip(' .'))


def gate(snap):
    R = load(snap); o = observe(R); S = o['sides']
    names = {s: cstr(R, 0x582f9 + 16 * (s - 1)) for s in range(1, 6)}
    groups = [(s, g) for s in range(1, 5) for g in S[s]['groups'] if g['alive'] and g['lead']]
    houses = []
    for s in range(1, 5):
        for l in S[s]['lords']:
            b = next((x for x in S[s]['settlements'] if x['lord'] == l['idx'] and x['category'] in (2, 0x10)), None)
            if b: houses.append((l, b))
    cmds = [f'callcap 9036 20000 A3={0x51538 + 0x13c * s + 2 * g["k"]:x}' for s, g in groups]
    for l, b in houses: cmds += ['w 2df96 00010001', f'callcap 95f6 60000 A3={b["addr"]:x}']
    ccs = parse_callcaps(repl(ROOT / snap, cmds))
    ok = tot = 0; bad = []
    def chk(name, a, b):
        nonlocal ok, tot
        tot += 1; ok += a == b
        if a != b: bad.append((name, a, b))
    for (s, g), cc in zip(groups, ccs[:len(groups)]):
        t = panel_text(R, cc); f = [field(t[i]) for i in range(1, 9)]
        tag = f'side {s} group {g["k"]}'
        chk(tag + ' Job', g['state_name'], f[1]); chk(tag + ' posture', g['posture_name'], f[2].split(' but ')[-1])
        chk(tag + ' Food', str(g['food']), f[6]); chk(tag + ' Troops', str(g['men']), f[7])
    for (l, b), cc in zip(houses, ccs[len(groups):]):
        t = panel_text(R, cc); f = [field(r) for r in t[1:8]]
        tag = f'lord {l["idx"]} via building {b["idx"]}'
        chk(tag + ' House Name', 'WorkShop' if b['category'] == 0x10 else b['kind_name'], f[0])   # gate_panels: category $10 shows kind 7
        chk(tag + ' Kingdom', names[b['owner']], f[3]); chk(tag + ' Food', str(l['food']), f[4])
        chk(tag + ' Men', f'{l["men_home"]} who are {l["loyalty_word"]}', f[5])
        exp = [f'{n} {k.capitalize()}' + ('s' if n != 1 else '') for k, n in l['goods'].items() if n]
        chk(tag + ' Stock', [e.split()[0] for e in exp], [e.split()[0] for e in stock_of(t)])
    return ok, tot, bad, len(groups), len(houses)


if __name__ == '__main__':
    import os; os.chdir(ROOT)
    G = T = 0
    for snap in sys.argv[1:] or DEFAULT:
        ok, tot, bad, ng, nh = gate(snap)
        print(f'{Path(snap).stem}: {ok}/{tot} fields ({ng} captain panels, {nh} house panels)')
        for b in bad[:8]: print('   MISMATCH', b)
        G += ok; T += tot
    print(f'TOTAL {G}/{T}')
