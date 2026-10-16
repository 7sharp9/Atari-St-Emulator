"""gate_probe.py - the mode $10 water veto, 68000 against tools/pm_fsm_ref.h_mode10, per walking man of a snapshot.

For every man stuck_census_exact.men() lists (owner 1..127, byte 6 == 0, mode $10/$12/$48/$4a) the REPL runs
`callcap 14f08 20000 - A2=00047970 A1=<record> D6=<word 8> D7=<word 10>` (the registers the object pass sets: A2
the bucket heads at $14b68, which the relink $163ea indexes at $1644e, and D6/D7 from $14ba0's movem.w 8(A1)) and the model runs h_mode10 on a copy of the same RAM; the gate compares the byte the call leaves in 31(A1)
(the mode: $4a = the $14f82 probe met water, $12 = open, the prev mode = reached).

Labelled poke: `w 16236 4e714e71` replaces `bne $14b72` (bytes 6600 e93a, the object-loop back-branch after
`lea 50(A1),A1 / cmpa.l #$57f66,A1` at $1622c) with two nops, so the call returns after the one record instead of
running the rest of the object pass. Control: --control runs the first K men without the poke (the call then walks the
rest of the array and its step cap must allow it) and checks 31(A1) agrees with the poked run.

Usage (from M68000/): uv run python reversing/powermonger/py/fsm/gate_probe.py [--control K] <snap> [...]
Work files: ${PM_WORK:-scratchpad/pm162}/water/gate_probe."""
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

here = Path(__file__).resolve()
sys.path.insert(0, str(here.parent))
import stuck_census_exact as sce  # noqa: E402
ref = sce.astar.ref

ROOT = sce.ROOT
WORK = ROOT / os.environ.get('PM_WORK', 'scratchpad/pm162') / 'water' / 'gate_probe'
WORK.mkdir(parents=True, exist_ok=True)
DLL = ROOT / 'bin' / 'Debug' / 'net8.0' / 'M68000.dll'
OBJ = 0x51b66


def model(ram, i):
    m = ref.Mem(ram)
    A1 = OBJ + 50 * i
    try:
        ref.h_mode10(m, A1, m.wu(A1 + 8), m.wu(A1 + 10))
    except AssertionError as e:
        return None, str(e)[:40]
    return m.bu(A1 + 31), None


def callcaps(snap, ids, poke, steps, tag):
    repl = WORK / (tag + '.repl')
    r = sce.astar.Map(snap).ram
    with open(repl, 'w') as f:
        if poke:
            f.write('w 16236 4e714e71\n')
        for i in ids:
            A1 = OBJ + 50 * i
            f.write('callcap 14f08 %d - A2=00047970 A1=%08x D6=%08x D7=%08x\n' % (steps, A1, int.from_bytes(r[A1 + 8:A1 + 10], 'big'),
                                                                    int.from_bytes(r[A1 + 10:A1 + 12], 'big')))
        f.write('q\n')
    out = WORK / (tag + '.out')
    env = dict(os.environ, ATARI_NOTRACE='1')
    with open(repl) as fi, open(out, 'w') as fo, open(WORK / (tag + '.err'), 'w') as fe:
        subprocess.run(['dotnet', 'exec', str(DLL), 'resume', str(snap), 'repl'], stdin=fi, stdout=fo, stderr=fe,
                       cwd=ROOT, env=env, check=False)
    blocks = re.split(r'(?m)^--- callcap \$014f08: ', open(out).read())[1:]
    assert len(blocks) == len(ids), 'expected %d callcaps, parsed %d (%s)' % (len(ids), len(blocks), out)
    res = []
    for i, b in zip(ids, blocks):
        assert b.startswith('returned'), b[:120]
        a = OBJ + 50 * i + 31
        mm = re.search(r'mem \$%06x \$[0-9a-f]{2}->\$([0-9a-f]{2})' % a, b)
        res.append(int(mm.group(1), 16) if mm else r[a])
    return r, res


def run(snap, control):
    r = sce.astar.Map(snap).ram
    ids = sorted(sce.men(r))
    tag = Path(snap).stem
    _r, emu = callcaps(snap, ids, True, 20000, tag)
    c = Counter()
    bad = []
    for i, e in zip(ids, emu):
        p, why = model(bytearray(r), i)
        if p is None:
            c['model out of scope (%s)' % why] += 1
            continue
        c['compared'] += 1
        c['match'] += p == e
        c['emu mode %02x' % e] += 1
        if p != e:
            bad.append((i, p, e))
    print('%s: %d walking men; %s' % (snap, len(ids), dict(sorted(c.items()))))
    for b in bad[:10]:
        print('   MISMATCH obj%d model %02x 68000 %02x' % b)
    if control:
        k = ids[:control]
        _r, emu2 = callcaps(snap, k, False, 2000000, tag + '_ctl')
        agree = sum(a == b for a, b in zip(emu[:control], emu2))
        print('   control (no poke, whole object pass): 31(A1) agrees with the poked call on %d/%d' % (agree, len(k)))
    return c['match'], c['compared']


if __name__ == '__main__':
    args = sys.argv[1:]
    control = 0
    if args and args[0] == '--control':
        control = int(args[1])
        args = args[2:]
    T = N = 0
    for s in args:
        t, n = run(s, control)
        T += t
        N += n
    print('TOTAL %d/%d' % (T, N))
