"""gate_maps.py: callcap differential test of the land-map routines vs maps_ref.py (140th pass, `maps`).

For 8 random lands (pm67_ok_pre + the build poke of build_land.sh, k = 0,1,5,10,25,60,100,142) and 8 stored campaign lands
(land1_pick_end.snap + mkland.py pokes, lands 0,3,12,19,38,150,162,173), stop at the natural entry of each routine, callcap it
(real 68000 delta) and run the transcription on the same RAM:

    $10410 smooth (first hit), $ac20 whole script decoder (flat discs, group starts, roads, stamps),
    $10910 road (first hit), $10638 town ground (first hit), $10058 colour/flag bake.

    cd M68000 && .venv/bin/python reversing/powermonger/py/maps/gate_maps.py [reuse]

Data under scratchpad/pm140/agents/maps/gate/.  Prints per routine matched/total tracked bytes (a byte is tracked if either
side changed it inside the planes, the town list $4b9f2.., the group blocks $51538.. or the script $58152..).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
HERE = Path(__file__).resolve().parent
DATA = ROOT / "scratchpad/pm140/agents/maps"      # outputs go to the gitignored scratchpad, not next to the script
DATA.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(HERE))
from disassemble import ram_from_snap
import maps_ref as M

OUT = DATA / 'gate'
OUT.mkdir(exist_ok=True)
DISK = 'scratchpad/powermonger.st'
ENV = dict(os.environ, ATARI_NOTRACE='1')
RAND = [0, 1, 5, 10, 25, 60, 100, 142]
STORED = [0, 3, 12, 19, 38, 150, 162, 173]
REGIONS = [(0x3f86c, 0x47a00), (0x4b9f2, 0x4ba40), (0x51538, 0x51b66), (0x58152, 0x58240)]
TARGETS = [('10410', 1), ('ac20', 1), ('10910', 1), ('10638', 1), ('10058', 1)]


def run(cmds, snap):
    p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a', DISK],
                       input='\n'.join(cmds) + '\nq\n', capture_output=True, text=True, cwd=ROOT, env=ENV, timeout=900)
    return p.stdout + p.stderr


def mkland(land):
    ram = ram_from_snap(str(ROOT / 'scratchpad/pm122/end/land1_pick_end.snap'))
    ent = ram[0x3f428 + land * 0x14c: 0x3f428 + (land + 1) * 0x14c]
    c = ['w 580a4 %04x%02x%02x' % (land, ent[0], ent[1])]
    for i in range(2, 0x14c, 4):
        ch = bytes(ent[i:i + 4])
        ch += bytes(ram[0x580a6 + i + len(ch): 0x580a6 + i + 4])
        c.append('w %x %s' % (0x580a6 + i, ch.hex()))
    return c


def captures(name, snap, pre):
    cmds = list(pre)
    for t, n in TARGETS:
        cmds += ['bpc %s %d 8000000' % (t, n), 'snap %s/%s_%s.snap' % (OUT.relative_to(ROOT).as_posix(), name, t)]
    run(cmds, snap)


def tracked(a):
    return any(lo <= a < hi for lo, hi in REGIONS)


def main():
    reuse = 'reuse' in sys.argv
    jobs = []
    for k in RAND:
        seed = '%08x' % (k * 0xb + 0x3fb)
        pages = '%04x0000' % (k * 0x96 + 0x672)
        jobs.append(('r%d' % k, 'scratchpad/pm67_ok_pre.snap',
                     ['w 2df92 001400b1', 'w 2df8e 001400b1', 'w 2df96 00010001', 'u 13b9a 80000000',
                      'w 580a0 ' + seed, 'w 5809c ' + pages]))
    for L in STORED:
        jobs.append(('s%d' % L, 'scratchpad/pm122/end/land1_pick_end.snap', mkland(L)))
    tot = {t: [0, 0, 0] for t, _ in TARGETS}   # tracked, ok, calls
    bad_calls = []
    skipped = []
    for name, snap, pre in jobs:
        if not reuse:
            captures(name, snap, pre)
        for t, _ in TARGETS:
            sp = OUT / ('%s_%s.snap' % (name, t))
            if not sp.exists():
                bad_calls.append((name, t, 'no snapshot'))
                continue
            js = OUT / ('%s_%s.json' % (name, t))
            if not (reuse and js.exists()):
                run(['callcap %s 60000000 %s' % (t, js.relative_to(ROOT).as_posix())], str(sp.relative_to(ROOT)))
            j = json.load(open(js))
            if j.get('outcome') != 'returned':
                bad_calls.append((name, t, j.get('outcome')))
                continue
            ram0 = ram_from_snap(str(sp))
            real = {}
            for a, b0, b1 in j['mem']:
                if tracked(a):
                    real[a] = b1
            m = bytearray(ram0)
            # entry registers from the snapshot's own CPU state are not in RAM: read them from the callcap json (reg0)
            reg0 = j['reg0']  # D0..D7, A0..A7
            if t == '10410':
                M.smooth_10410(m)
            elif t == 'ac20':
                M.dec_oth_ac20(m)
            elif t == '10910':
                if (reg0[0] & 0xffff) >= 0x2000 or (reg0[1] & 0xffff) >= 0x2000:
                    skipped.append((name, t, 'entry registers are not a road call (D0=$%x D1=$%x): bpc landed on a non-call hit' % (reg0[0] & 0xffff, reg0[1] & 0xffff)))
                    continue
                M.do_road_10910(m, reg0[0] & 0xffff, reg0[1] & 0xffff, M.s16(reg0[4]), M.s16(reg0[5]))
            elif t == '10638':
                if (reg0[2] & 0xffff) >= 64 or (reg0[3] & 0xffff) >= 128 or (reg0[4] & 0xffff) > 6:
                    skipped.append((name, t, 'entry registers are not a town call (D2=$%x D3=$%x D4=$%x)' % (reg0[2] & 0xffff, reg0[3] & 0xffff, reg0[4] & 0xffff)))
                    continue
                M.town_gr_10638(m, reg0[2] & 0xffff, reg0[3] & 0xffff, reg0[4] & 0xffff)
            elif t == '10058':
                M.bake_10058(m)
            mine = {}
            for lo, hi in REGIONS:
                for a in range(lo, hi):
                    if m[a] != ram0[a]:
                        mine[a] = m[a]
            keys = set(real) | set(mine)
            bad = [a for a in keys if real.get(a, ram0[a]) != mine.get(a, ram0[a])]
            tot[t][0] += len(keys)
            tot[t][1] += len(keys) - len(bad)
            tot[t][2] += 1
            if bad:
                bad_calls.append((name, t, 'mismatch x%d first $%x real %s mine %s' % (
                    len(bad), min(bad), real.get(min(bad), ram0[min(bad)]), mine.get(min(bad), ram0[min(bad)]))))
            print('%-5s %-6s steps=%-8s changed=%-5d %s' % (name, t, j.get('steps'), len(keys), 'ok' if not bad else 'MISMATCH x%d' % len(bad)))
    print()
    for t, (n, ok, calls) in tot.items():
        print('$%s: %d/%d tracked bytes identical over %d callcaps' % (t, ok, n, calls))
    for b in skipped:
        print('SKIP', b)
    for b in bad_calls:
        print('FAIL', b)


if __name__ == '__main__':
    main()
