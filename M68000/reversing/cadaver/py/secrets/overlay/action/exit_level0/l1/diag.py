"""diag.py <subcommand> ...: read-only diagnostics for driving Cadaver level 1 (92nd pass).  Each runs a snapshot in a Repl and prints; nothing is written.

  regions  <snap> <room>...              the region list of each room, static, from the snapshot's room records: (x_lo y_lo x_hi y_hi z_lo z_hi).  A region is a rectangle the hero
                                         (event 15) or another object (event 17) overlaps with its bbox [trail, lead]; many level-1 traps and plates are regions (room 1: 0 0 47 15)
  creatures <snap> <n> <chunk>           every placement entry with id >= 900 (instances CREATEd at room entry: hounds, flyers) each chunk, the hero standing still
  ents     <snap> <id,id,..> <n> <chunk> the placement entries of those ids each chunk (rect, z top, z bottom), with hero position and health
  jumparc  <snap> <n> <chunk> [k dir]    hold FIRE for n chunks printing the hero z each chunk (the arc, ceilings); with k and dir, add that direction from chunk k (it does not
                                         move the hero: the takeoff direction fixes the arc)
  hpwatch  <snap> <dir|-> <n> <chunk>    `watch` the health word: print the step and PC of every write while holding dir (or standing) and the ids >= 900 at the first
  poison   <snap> <n> <chunk>            health and the POISON strength byte 2434(A5) each time either changes (strength 10: a tick costs 10; verb 90's 10, 40, 10 gives about 3-4 ticks)
Snapshots are relative to M68000/ or absolute.  Root from M68000_ROOT or this file's location."""
import sys, os, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault('ATARI_NOTRACE', '1')
from explore import *            # Repl, A5, ROOM, K, joy, pos, hp, zz, ent, ...
from pathlib import Path


def regions(snap, rooms):
    root = Path(os.environ['M68000_ROOT'])
    sys.path.insert(0, str(root / 'reversing/cadaver/py')); sys.path.insert(0, str(root / 'tools'))
    from gfxview import load_ram, snapshot_regs
    from room_object_census import resource_type, resolve
    ram, base = load_ram(snap); a5 = snapshot_regs(snap)[0]['a5']; ri, rd, rc = resource_type(ram, base, a5, 3)
    for s in rooms:
        a = resolve(ram, base, ri, rd, s)
        if a is None: print('room', s, 'none'); continue
        size = struct.unpack_from('>H', ram, ri + s * 4 - base)[0]; p = a + 0x20
        for i in range(ram[a + 31]): p += ram[p]
        n = ram[p] if size - (p - a) else 0
        print('room', s, 'regions', n, [tuple(ram[p + 2 + 6 * i + j] for j in range(6)) for i in range(n)] if n else '')


def table(r, ids=None):
    tbl = r.l(A5 + 56); cnt = r.w(A5 + 1152); out = []
    for i in range(cnt):
        e = r.mem(tbl + 0x46 * i, 0x46); t = int.from_bytes(e[10:14], 'big')
        if 0x1000 < t < 0x7ffff:
            oid = r.w(t + 4)
            if (oid >= 900 if ids is None else oid in ids): out.append((oid, tuple(e[0:4]), e[5], e[4]))
    return out


def main(a):
    cmd = a[0]
    if cmd == 'regions':
        return regions(a[1], [int(v) for v in a[2:]])
    r = Repl(os.path.abspath(a[1]))
    if cmd == 'creatures':
        n, ch = int(a[2]), int(a[3])
        for i in range(n): print(i * ch, hp(r), table(r), flush=True); r.cmd('s %d' % ch)
    elif cmd == 'ents':
        ids = [int(v) for v in a[2].split(',')]; n, ch = int(a[3]), int(a[4])
        for i in range(n): print(i * ch, hp(r), pos(r), [(o, ent(r, o)) for o in ids], flush=True); r.cmd('s %d' % ch)
    elif cmd == 'jumparc':
        n, ch = int(a[2]), int(a[3]); k = int(a[4]) if len(a) > 4 else None; d = K[a[5]] if len(a) > 5 else 0
        joy(r, FIRE)
        for i in range(n):
            if k is not None and i == k: joy(r, FIRE | d)
            r.cmd('s %d' % ch); print(i, pos(r), zz(r), flush=True)
        joy(r, 0)
        for i in range(8): r.cmd('s %d' % ch); print('rel', i, pos(r), zz(r), flush=True)
    elif cmd == 'hpwatch':
        d, n, ch = a[2], int(a[3]), int(a[4]); r.err.clear(); r.cmd('watch %x 2' % (A5 + 1174))
        if d != '-': joy(r, K[d])
        seen = 0
        for i in range(n):
            r.cmd('s %d' % ch); ws = [l for l in r.err if 'WATCH' in l]
            if len(ws) > seen:
                for l in ws[seen:]: print(i * ch, pos(r), l)
                print('    ids>=900:', table(r)); seen = len(ws)
    elif cmd == 'poison':
        n, ch = int(a[2]), int(a[3]); prev = None
        for i in range(n):
            v = (hp(r), r.b(A5 + 2434))
            if v != prev: print(i * ch, v, flush=True); prev = v
            r.cmd('s %d' % ch)
    else: raise SystemExit(__doc__)
    r.close()


if __name__ == '__main__':
    main(sys.argv[1:])
