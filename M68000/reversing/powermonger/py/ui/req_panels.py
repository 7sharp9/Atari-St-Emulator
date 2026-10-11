"""Render the grids the requester openers build, by callcap from a snapshot (strategy.md panel table, system.md `_do_req`).

    cd M68000 && uv run python reversing/powermonger/py/ui/req_panels.py [snap]

Openers and their entry contracts, read from their bodies:
  $c706 offer of alliance (A3 = $51538 + group offset; verb from the posture 60(A3), tribute from the goods words 84(A3)+12j)
  $c9f8 "An Alliance has been forged" (D0, D1 = the two sides)
  $cada refusal, one of four templates by $57fec & 3 (D0 = the refusing side)
  $cd42 "DISK STATUS REQUESTER" (A3 = two 30-byte lines; $13f26 is the Load Data Disk pair)
Every callcap must return; the grid printed is the panel slot with the most changed bytes (uilib.panel_text).
The run log goes to $PM_WORK (default scratchpad/pm150/ui_unread) as req_panels.out. Exit 1 if any callcap fails to return.
"""
import os
import sys
from pathlib import Path


def find_root():
    p = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve())
    for q in [p, *p.parents]:
        if (q / 'tools/rdis.py').exists():
            return q
    sys.exit('repo root (the directory holding tools/rdis.py) not found')


ROOT = find_root()
os.environ.setdefault('M68000_ROOT', str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from uilib import ram_of, repl, parse_callcaps, panel_text  # noqa: E402

WORK = ROOT / os.environ.get('PM_WORK', 'scratchpad/pm150/ui_unread')
snap = ROOT / (sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/pm123/win/m1_ready.snap')
R = ram_of(snap)
side = int.from_bytes(R[0x57ffe:0x58000], 'big')
g0 = 0x51538 + side * 0x13c + 0x4c                     # the local side's group 0, in $33b0's A3 convention
tick_lo = int.from_bytes(R[0x57fee:0x57ff0], 'big')    # w writes a longword: keep the word after $57fec
cases = [
    ('c706 offer, posture 3, 2 of goods 0',
     [f'w {g0 + 60:x} 00030000', f'w {g0 + 84:x} 00020000', f'callcap c706 20000 A3={g0:x}']),
    ('c9f8 forged, sides 1 and 3', ['callcap c9f8 20000 D0=1 D1=3']),
] + [(f'cada refusal, $57fec & 3 = {t}', [f'w 57fec {t:04x}{tick_lo:04x}', 'callcap cada 20000 D0=3']) for t in range(4)] + [
    ('cd42 disk requester, lines $13f26', ['callcap cd42 20000 A3=13f26']),
]
bad = 0
log = []
for tag, cmds in cases:
    out = repl(snap, ['disk scratchpad/powermonger.st'] + cmds)
    log.append(f'### {tag}\n{out}')
    cc = parse_callcaps(out)
    ok = bool(cc) and cc[-1]['returned']
    bad += not ok
    print(f'== {tag}: returned={ok}')
    for row in (panel_text(R, cc[-1]) or []) if cc else []:
        print('   |' + row + '|')
WORK.mkdir(parents=True, exist_ok=True)
(WORK / 'req_panels.out').write_text('\n'.join(log))
print(f'{len(cases) - bad}/{len(cases)} returned')
sys.exit(1 if bad else 0)
