"""posture_work.py - does the arriving group's posture choose what the lord's men gather? (`$5fa0` -> `$5cde`, D1 = `$30fe`)

    cd M68000 && uv run python reversing/powermonger/py/orders/posture_work.py [nat-dir]     # default scratchpad/pm141/agents/orders/nat (gate_orders' natural entries)

For every natural `$5fa0` entry snapshot `n5fa0*_N.snap` (registers from its .json) it pokes the group's posture word
(60 of the group view `$51538 + 42(A1)`, a longword write that keeps word 62) to 2, 3 and 4 in turn and runs
`callcap 5fa0` (one variable: the posture), then reads from the delta the lord's gather_kind word `12(L)`
(L = `$51b66 + 24(A3)`) and the returned D2 (the men's mode). Prints one row per entry: kind for posture 2/3/4
(`-` = not written: no WorkShop, the refusal) and the goods it feeds ((kind>>1)-1: Pike Sword Bow Plough Boat Pot
Catapult Cannon). Output also in $PM_WORK/posture/ (default scratchpad/pm150/weather).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap  # noqa: E402

NAT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'scratchpad/pm141/agents/orders/nat'
OUT = Path(os.environ.get('PM_WORK', ROOT / 'scratchpad/pm150/weather')) / 'posture'
OUT.mkdir(parents=True, exist_ok=True)
GOODS = ['Pike', 'Sword', 'Bow', 'Plough', 'Boat', 'Pot', 'Catapult', 'Cannon']
env = dict(os.environ, ATARI_NOTRACE='1')
summary = {}
for jf in sorted(NAT.glob('n5fa0*.json')):
    for e in json.load(open(jf)):
        snap = ROOT / e['snap'] if not os.path.isabs(e['snap']) else Path(e['snap'])
        if not snap.exists():
            continue
        r = ram_from_snap(str(snap))
        w = lambda a: int.from_bytes(r[a:a + 2], 'big')
        sw = lambda a: int.from_bytes(r[a:a + 2], 'big', signed=True)
        a1, a3 = e['regs']['A1'] & 0xffffff, e['regs']['A3'] & 0xffffff
        grp = 0x51538 + sw(a1 + 42)
        lord = 0x51b66 + sw(a3 + 24)
        cmds = []
        for p in (2, 3, 4):
            cmds += ['w %x %04x%04x' % (grp + 60, p, w(grp + 62)), 'callcap 5fa0']
        cmds.append('q')
        name = snap.stem
        (OUT / f'{name}.cmds').write_text('\n'.join(cmds) + '\n')
        res = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', str(snap), 'repl'],
                             input='\n'.join(cmds) + '\n', capture_output=True, text=True, cwd=ROOT, env=env)
        (OUT / f'{name}.txt').write_text(res.stdout + res.stderr)
        runs = res.stdout.split('--- callcap $005fa0')[1:]
        row = []
        for p, txt in zip((2, 3, 4), runs):
            lo = re.search(r'mem \$%06x \$[0-9a-f]+->\$([0-9a-f]+)' % (lord + 13), txt)
            hi = re.search(r'mem \$%06x \$[0-9a-f]+->\$([0-9a-f]+)' % (lord + 12), txt)
            if lo or hi:
                k = (int(hi.group(1), 16) if hi else r[lord + 12]) << 8 | (int(lo.group(1), 16) if lo else r[lord + 13])
                row.append('%x %s' % (k, GOODS[(k >> 1) - 1] if 2 <= k <= 16 else '?'))
            else:
                row.append('-')
        summary[name] = row
        print('%-22s posture2 %-12s posture3 %-12s posture4 %-12s (old kind %x)' % (name, row[0], row[1], row[2], w(lord + 12)))
written = [v for v in summary.values() if v.count('-') < 3]
print('entries %d, gather kind written in %d' % (len(summary), len(written)))
