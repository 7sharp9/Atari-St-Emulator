"""gate_worldmap.py: the conquest-map screen ($1120e family) vs maps_ref, from scratchpad/pm123/win/m1_map.snap.

    cd M68000 && .venv/bin/python reversing/powermonger/py/maps/gate_worldmap.py

 A. `$11422` (_draw_pa) by callcap with A1 = the live screen base, scroll word `$11420` poked to 0, 137, 408: the 32000-byte
    screen copy vs blit_11422.
 B. the on-screen picture of the snapshot itself: base = shifter base, scroll = word[$11420]: the live screen vs blit_11422 on RAM.
 C. `$11458` (_draw_da) by callcap after poking 12 random conquered/free/unselectable patterns into `$3f2a0`: the real delta in the
    97280-byte bitmap vs draw_da_11458 (bytes identical / bytes changed by either).
 D. the pointer test `$11252..$112f6`: pick_1120e vs the box the game draws (live: mouse hovered over cells, 120000 steps, the
    17 x 33 box found in the screen) is in gate_pick.py.
"""
import json, os, random, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
HERE = Path(__file__).resolve().parent
DATA = ROOT / "scratchpad/pm140/agents/maps"      # outputs go to the gitignored scratchpad, not next to the script
DATA.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(HERE))
from disassemble import ram_from_snap
from gfxview import load_video_regs
import maps_ref as M
SNAP = 'scratchpad/pm123/win/m1_map.snap'
OUT = DATA / 'gate'; OUT.mkdir(exist_ok=True)
ENV = dict(os.environ, ATARI_NOTRACE='1')


def run(cmds):
    subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl', '--disk-a', 'scratchpad/powermonger.st'],
                   input='\n'.join(cmds) + '\nq\n', capture_output=True, text=True, cwd=ROOT, env=ENV, timeout=600)


ram = bytearray(ram_from_snap(str(ROOT / SNAP)))
base = load_video_regs(str(ROOT / SNAP))['base']
print('screen base $%x, scroll word $11420 = %d, conquered table nonzero at %s' % (
    base, M.w16(ram, M.BMSCROLL), [i for i in range(195) if ram[M.CONQ + i]]))
# B
scr = ram[base:base + 32000]
exp = ram[M.MAPBMP + M.w16(ram, M.BMSCROLL) * 160: M.MAPBMP + M.w16(ram, M.BMSCROLL) * 160 + 32000]
print('B live screen vs bitmap window: %d/32000 bytes identical' % sum(1 for a, b in zip(scr, exp) if a == b))
# A
tot = 0
for sc in (0, 137, 408):
    js = OUT / ('wm_blit_%d.json' % sc)
    run(['w 1141e %04x%04x' % (0, sc), 'callcap 11422 20000000 %s A1=%x' % (js.relative_to(ROOT).as_posix(), base)])
    j = json.load(open(js)) if js.exists() else {'outcome': 'returned, no byte changed (no json written)', 'mem': []}
    r2 = bytearray(ram); r2[M.BMSCROLL:M.BMSCROLL + 2] = sc.to_bytes(2, 'big')
    real = bytearray(r2)
    for a, b0, b1 in j['mem']:
        if a < len(real): real[a] = b1
    M.blit_11422(r2, base, sc)
    n = sum(1 for a in range(base, base + 32000) if real[a] == r2[a]); tot += n
    print('A scroll %3d: %s, %d/32000 screen bytes identical' % (sc, j['outcome'], n))
print('A total %d/%d' % (tot, 3 * 32000))
# C
rnd = random.Random(140)
tc = tn = 0
for case in range(12):
    tab = bytearray(196)
    for i in range(195):
        tab[i] = rnd.choice([0, 0, 1, 1, 0x80, 2]) if case else (1 if i % 2 else 0)
    cmds = ['w %x %s' % (M.CONQ + i, tab[i:i + 4].hex()) for i in range(0, 196, 4)]
    js = OUT / ('wm_dagger_%d.json' % case)
    run(cmds + ['callcap 11458 20000000 %s' % js.relative_to(ROOT).as_posix()])
    j = json.load(open(js)) if js.exists() else {'outcome': 'returned, no byte changed (no json written)', 'mem': []}
    r2 = bytearray(ram); r2[M.CONQ:M.CONQ + 196] = tab
    real = bytearray(r2)
    for a, b0, b1 in j['mem']:
        if M.MAPBMP <= a < M.MAPBMP + 97280: real[a] = b1
    mine = bytearray(r2); M.draw_da_11458(mine)
    keys = [a for a in range(M.MAPBMP, M.MAPBMP + 97280) if real[a] != r2[a] or mine[a] != r2[a]]
    ok = sum(1 for a in keys if real[a] == mine[a]); tc += ok; tn += len(keys)
    print('C case %2d: %d conquered, %s, %d/%d changed bytes identical' % (case, sum(1 for x in tab[:195] if 0 < x < 128), j['outcome'], ok, len(keys)))
print('C total %d/%d' % (tc, tn))
