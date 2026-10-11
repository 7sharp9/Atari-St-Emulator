"""Per merchant goods move caught by `bpc 159f0` (pickup decrement) or `bpc 159ba` (drop increment):
the caller, the merchant's home lord, the lord whose goods change, and the slot.

$159de: A0 = source lord, r = $57fec % 6 (D0.w at $159f0), goods at 24(A0,D0.w).
$159a4: A0 = destination lord, D0.w = code >> 1, goods at 23(A0,D0.w).
Home lord of merchant A1: $4e514 + word[$4f916 + word[A1+34] + 14].
Usage (from M68000/, work dir from $PM_WORK, default scratchpad/pm150/docfix_econ_gfx):
    python3 merch_moves.py
"""
import os
import re
import struct
import sys
from pathlib import Path

here = Path(__file__).resolve()
root = next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(root / 'tools'))
from pm_export import ram_from_snap  # noqa: E402

work = root / os.environ.get('PM_WORK', 'scratchpad/pm150/docfix_econ_gfx')
NAMES = ['Pike', 'Sword', 'Bow', 'Plough', 'Boat', 'Pot', 'Catapult', 'Cannon']


def regs(log):
    out, cur = {}, None
    for line in log.read_text().splitlines():
        if line.startswith('--- breakpoint'):
            cur = {}
        elif cur is not None and re.match(r'^[DA]\d:', line):
            cur.update({k: int(v, 16) for k, v in re.findall(r'([DA]\d):([0-9a-f]{8})', line)})
        m = re.match(r'Snapshot written to (\S+) at', line)
        if m and cur:
            out[m.group(1)] = cur
            cur = None
    return out


for pc in ('159f0', '159ba'):
    log = work / 'merch' / f'{pc}.out'
    if not log.exists():
        continue
    for snap, r in regs(log).items():
        b = ram_from_snap(root / snap)
        w = lambda a: struct.unpack('>H', b[a:a + 2])[0]
        ret = struct.unpack('>I', b[r['A7']:r['A7'] + 4])[0]
        a1 = r['A1']
        home = (w(0x4f916 + w(a1 + 34) + 14)) // 32
        lord = (r['A0'] - 0x4e514) // 32
        d0 = r['D0'] & 0xffff
        slot = d0 if pc == '159f0' else d0 - 1
        print(pc, Path(snap).name, 'caller', hex(ret - 6), 'merchant', hex(a1), 'mode', hex(b[a1 + 31]),
              'home', home, 'goods lord', lord, 'slot', slot, NAMES[slot] if 0 <= slot < 8 else '?',
              'same' if home == lord else 'OTHER')
