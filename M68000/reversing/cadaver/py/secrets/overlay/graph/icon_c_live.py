"""icon_c_live.py: A1 (Cadaver 91st pass).  Is the APPLY icon ($c) offered for the class-4 / class-16 targets that carry event-18 blocks?
Live in the real game: from the lineage snapshot (room 90) an INJECTED teleport (labelled: a scratch `37 room x y z` written over object 562's
event-5 block, then the event queued) puts the hero in the target's room; the live placement entry of the target gives its live class byte
`22(6(entry))` (what $0096e6 stores in 2476(A5)); then the item-panel icon builder $009f02 is callcap'd with 1236(A5) = a held item, 2128(A5) = the target,
2476(A5) = that live class, and the icon list at $5ff6 is read.  Control: a class-11 keyhole (720 in room 53 is far; 485 in room 21 is used).
Usage: icon_c_live.py ROOM OBJID [OBJID ...]"""
import sys, os, json
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
from h import H, set_body, inject5, A5, TMP
LIN = os.path.abspath(os.environ.get('CAD_LINEAGE_SNAP', ROOT + '/scratchpad/cadaver/s90/run1/end_room90.snap'))

def run(room, objs, item=718):
    h = H(LIN); r = h.r
    h.owner = 562
    print('start room', r.w(A5 + 1166), 'ruck count', r.b(A5 + 2438))
    set_body(h, [0x25, room, 4, 4, 0])
    inject5(h, 562, 0, 5)
    r.cmd('s 400000')
    print('room now', r.w(A5 + 1166))
    base = r.l(A5 + 56); n = r.w(A5 + 1152)
    res = {}
    for i in range(n):
        e = r.mem(base + 70 * i, 70)
        rec = int.from_bytes(e[10:14], 'big')            # type-6 record pointer? (drv.idmap reads the id at +4 of it)
        live = int.from_bytes(e[6:10], 'big')
        oid = r.w(rec + 4) if 0x1000 < rec < 0x7ffff else None
        if oid in objs:
            res[oid] = dict(idx=i, bbox=list(e[0:6]), live=hex(live), cls=r.b(live + 22), b23=r.b(live + 23), b12=r.b(live + 12))
    print('placement entries for', objs, res)
    return h, res

if __name__ == '__main__':
    room = int(sys.argv[1]); objs = [int(x) for x in sys.argv[2:]]
    h, res = run(room, objs)
    h.close()

def dump(h, a, n=48): return h.r.mem(a, n).hex(' ', 2)
