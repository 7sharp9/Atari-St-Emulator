"""Provoking (`$201b4`, the store at `$20206`): at every entry of $201b4 record the impact point (D0 x, D2 z, the shot's y at -16(A6)) and
the whole actor pool; at every stop at $20206 (the `move.l #$21f00,16(A0)`) record A0's record BEFORE the store, step once and read
+16 AFTER. Check per conversion: the record's behaviour before was a patrol ($21c64, $21d08, $21df6), life bit 14 was set at the
scan's entry, and every axis |record - impact| is within -$800..+$7ff (the scan's window); and, per scan, that every patrol record inside
the window was converted and none outside was.

    python3 provoke_check.py <snapshot> <steps> [<snapshot> <steps> ...]
Natural runs (no pokes). Prints one line per scan and the totals. Writes nothing."""
import os, struct, sys

import bh
R = bh.ROOT
from stclient import StServer

hx = lambda v: int(str(v).lstrip('$'), 16)
s16 = lambda v: (v & 0xffff) - 0x10000 if v & 0x8000 else v & 0xffff
PATROL = (0x21c64, 0x21d08, 0x21df6)

def pool(s):
    n = struct.unpack('>h', bytes.fromhex(s('read', addr=0x32a3e, len=2)))[0]
    raw = bytes.fromhex(s('read', addr=0x31d54, len=20 * n)) if n else b''
    return [struct.unpack('>6hhhI', raw[20 * i:20 * i + 20]) for i in range(n)]

def finish(scan, tot):
    """Completeness of a scan: every record that was a patrol with life bit 14 inside the window at the entry was converted, no other."""
    if not scan:
        return
    imp = scan['imp']
    want = {i for i, r in enumerate(scan['pool']) if r[8] in PATROL and r[6] & 0x4000
            and all(-0x800 <= s16(r[k] - imp[k]) < 0x800 for k in range(3))}
    got = {c[0] for c in scan['conv']}
    out = [i for i, r in enumerate(scan['pool']) if r[8] in PATROL and r[6] & 0x4000 and i not in want]
    tot['outside_not_converted'] = tot.get('outside_not_converted', 0) + len(out)
    tot['scans'] += 1; tot['scans_ok'] += want == got
    print(f"  scan at step {scan['step']} impact {imp}: expected {sorted(want)} converted {sorted(got)} (patrols outside the window, left alone: {len(out)}) {'ok' if want == got else 'MISMATCH'}")

def run(snap, steps, tot):
    s = StServer(R)
    try:
        s('load', snapshot=os.path.abspath(snap))
        s('bp_set', addrs=[0x201b4, 0x20206])
        left = steps; scan = None
        while left > 0:
            r = s('run', max_steps=min(left, 5_000_000)); left -= r['steps']
            if r['reason'] != 'breakpoint':
                continue
            pc = hx(r['pc']); rg = s('regs')
            if pc == 0x201b4:
                finish(scan, tot)
                a6 = hx(rg['a6'])
                imp = (s16(hx(rg['d0'])), s16(struct.unpack('>h', bytes.fromhex(s('read', addr=a6 - 16, len=2)))[0]), s16(hx(rg['d2'])))
                scan = {'imp': imp, 'pool': pool(s), 'conv': [], 'step': r['step']}
            elif pc == 0x20206 and scan:
                a0 = hx(rg['a0']); i = (a0 - 0x31d54) // 20
                before = scan['pool'][i]
                s('step', n=1)
                after = struct.unpack('>I', bytes.fromhex(s('read', addr=a0 + 16, len=4)))[0]
                scan['conv'].append((i, before, after))
                # the scan ends when the loop runs out: judge it at the next scan entry or at the end; do it now per conversion
                imp = scan['imp']
                d = [s16(before[0] - imp[0]), s16(before[1] - imp[1]), s16(before[2] - imp[2])]
                ok = before[8] in PATROL and (before[6] & 0x4000) and all(-0x800 <= x < 0x800 for x in d) and after == 0x21f00
                tot['conv'] += 1; tot['conv_ok'] += bool(ok)
                print(f"  step {r['step']} scan impact {imp} record {i} was {before[8]:#x} life {before[6] & 0xffff:#06x} d {d} +16 after {after:#x} {'ok' if ok else 'MISMATCH'}")
                continue
        finish(scan, tot)
    finally:
        s.close()

if __name__ == '__main__':
    a = sys.argv[1:]
    tot = {'scans': 0, 'scans_ok': 0, 'conv': 0, 'conv_ok': 0}
    for i in range(0, len(a), 2):
        print(a[i])
        run(a[i], int(a[i + 1]), tot)
    print(tot)
