"""lord_slots.py [dir]: per land, $4f914/32 (lord slots $2eac consumed) against the slots it filled (byte 0, the side,
non-zero), from lord_slots.sh's dumps. A consumed slot left empty is a failed $2eac call (corner altitudes summing to 0
mod 256, strategy.md "Towns, ranks and water"). Default dir scratchpad/pm168/lordslots under M68000/."""
import os, re, sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
os.chdir(ROOT)
D = Path(sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/pm168/lordslots')
tot = lost = bad = 0
for f in sorted(D.glob('k*.txt'), key=lambda p: int(p.stem[1:])):
    t = f.read_text()
    if t.count('reached') < 2:
        print(f.stem, 'BUILD NOT REACHED'); bad += 1; continue
    rows = [bytes.fromhex(l) for l in t.splitlines() if re.fullmatch(r'([0-9a-f]{2} )*[0-9a-f]{2}', l.strip())]
    count, hw, lords = rows[0], rows[1], b''.join(rows[2:])
    if len(lords) != 2048:
        print(f.stem, 'BAD DUMP', len(lords)); bad += 1; continue
    n = int.from_bytes(hw, 'big') // 32
    empty = [i for i in range(n) if lords[32*i] == 0]
    filled_above = [i for i in range(n, 64) if lords[32*i] != 0]
    tot += 1; lost += bool(empty)
    print(f.stem, 'lords_param', int.from_bytes(count, 'big'), 'consumed', n, 'empty', empty,
          'filled_above_hw', filled_above, 'empty_cells', [hex(int.from_bytes(lords[32*i+4:32*i+6], 'big')) for i in empty])
print(f'{tot} lands read, {lost} with a consumed slot left empty, {bad} unread')
