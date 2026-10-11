"""Per natural $550e capture of scratchpad/pm122/agents/revolt/nat: the caller (return address at [A7]),
the lord's loyalty_pressure (word 14(A0)) and side. Usage: python3 revolt_callers.py [nat-dir]  (default scratchpad/pm122/agents/revolt/nat under M68000/)"""
import re, struct, sys, os
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
os.chdir(ROOT)
D = Path(sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/pm122/agents/revolt/nat')
rows = {}
for log in sorted(D.glob('*.log')):
    cur = None
    for line in log.read_text().splitlines():
        if line.startswith('--- breakpoint'):
            cur = {}
        elif cur is not None and re.match(r'^[DA]\d:', line):
            cur.update({k: int(v, 16) for k, v in re.findall(r'([DA]\d):([0-9a-f]{8})', line)})
        m = re.match(r'Snapshot written to (\S+_550e)\.snap', line)
        if m and cur:
            rows[m.group(1)] = cur; cur = None
by = {}
for snap, r in sorted(rows.items()):
    b = Path(snap + '.ram').read_bytes()
    ret = struct.unpack('>I', b[r['A7']:r['A7'] + 4])[0]
    lp = struct.unpack('>h', b[r['A0'] + 14:r['A0'] + 16])[0]
    land = Path(snap).name.split('_')[0]
    by.setdefault((land, hex(ret)), []).append(lp)
    print(Path(snap).name, 'ret', hex(ret), 'lord', (r['A0'] - 0x4e514) // 32, 'loyalty', lp)
for k, v in sorted(by.items()):
    print(k, len(v), min(v), max(v))
