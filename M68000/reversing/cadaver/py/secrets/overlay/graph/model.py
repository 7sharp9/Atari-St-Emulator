"""model.py: A1 (Cadaver 91st pass) data model for the whole-corpus script dataflow graph.
Loads a snapshot's resource tables (types 3 rooms, 4 flags/doors, 5 room lists, 6 objects, 8 rucksack), reuses
`verb_decode.collect()` / `room_blocks.room_blocks()` for the script blocks (no hand parsing), and turns every block into
(owner, event, gate, verb rows with the IF/ELSE context).  `effects.py` classifies each verb row into graph reads/writes.
Run as a library; `graph.py` is the driver."""
import os, sys, struct, collections
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT', Path(__file__).resolve().parents[6]))   # M68000/ (this file: M68000/reversing/cadaver/py/secrets/overlay/graph/)
sys.path.insert(0, str(ROOT / 'reversing/cadaver/py')); sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'reversing/cadaver/py/secrets/overlay'))
import verb_decode as vd
import room_blocks as rb
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve

L1 = os.environ.get('CAD_LEVEL1_SNAP', str(ROOT / 'scratchpad/cadaver/level1_loaded.snap'))          # the initial level-1 state
LINEAGE = os.environ.get('CAD_LINEAGE_SNAP', str(ROOT / 'scratchpad/cadaver/s90/run1/end_room90.snap'))   # the lineage state the chains start from (room 90, health 60)
OUTDIR = Path(os.environ.get('OUTDIR', ROOT / 'scratchpad/cadaver/s91_graph'))
VARBASE = 2282              # script variables: bytes at VARBASE(A5)
TIMERBASE = 2458            # timer table (timers 2458..)
IFVERBS = (14, 48, 58, 59)
CONDS = (16, 19, 30, 34, 40, 43, 47, 56, 57, 60, 61, 64, 76, 80, 88, 91)


def u16(ram, a): return (ram[a] << 8) | ram[a + 1]
def u32(ram, a): return struct.unpack_from('>I', ram, a)[0]


class Snap:
    """one snapshot's static + live resource state"""
    def __init__(self, path):
        self.path = path
        self.ram, self.base = load_ram(path)
        self.a5 = snapshot_regs(path)[0]['a5']
        self.tab = {t: resource_type(self.ram, self.base, self.a5, t) for t in (3, 4, 5, 6, 8)}

    def res(self, t, i):
        idx, dat, cnt = self.tab[t]
        if i >= cnt: return None
        return resolve(self.ram, self.base, idx, dat, i)

    # ---- type-2 class templates.  room_object_census.resolve() keeps only the low 16 bits of the 17-bit offset (entry long & $1ffff, size = entry >> 17):
    # 155 of the 249 level-1 templates (index 100 and up) sit past $10000 and resolve $10000 too low there.  This resolver uses the long.
    def tmpl2(self, t):
        idx, dat, cnt = resource_type(self.ram, self.base, self.a5, 2)
        if t >= cnt: return None
        e = u32(self.ram, idx + 4 * t)
        if (e >> 17) == 0: return None
        return dat + (e & 0x1ffff)

    def cls(self, oid):
        """(class b22, icon-selector b23, flags b12, b29) of the object's type-2 template (record +6)"""
        o = self.obj(oid)
        if o is None: return None
        a = self.tmpl2(o['tmpl'])
        if a is None: return None
        r = self.ram
        return dict(addr=a, b22=r[a + 22], b23=r[a + 23], b12=r[a + 12], b29=r[a + 29], name=u16(r, a + 10))

    # ---- objects (type 6)
    def obj_ids(self): return [i for i in range(1000) if self.res(6, i) is not None]
    def obj(self, oid):
        a = self.res(6, oid)
        if a is None: return None
        r = self.ram
        return dict(addr=a, b3=r[a + 3], tmpl=u16(r, a + 6), room=r[a + 10], b12=r[a + 12], b15=r[a + 15], b22=r[a + 22])

    # ---- rooms (type 3)
    def rooms(self):
        out = {}
        idx, dat, cnt = self.tab[3]
        for s in range(cnt):
            a = self.res(3, s)
            if a is None: continue
            r = self.ram
            size = u16(r, idx + 4 * s)
            x0, y0, w, h = r[a + 1], r[a + 3], r[a + 4], r[a + 5]
            doors = [u16(r, a + 6 + 2 * i) for i in range(7)]
            doors = [d for d in doors if d != 0xffff]
            endblocks = r[a]
            tail = size - endblocks
            regions = []
            if tail >= 2 and r[a + endblocks] and tail == 2 + 6 * r[a + endblocks]:
                n = r[a + endblocks]
                for k in range(n):
                    p = a + endblocks + 2 + 6 * k
                    regions.append(tuple(r[p:p + 6]))
            out[s] = dict(slot=s, addr=a, rect=(x0, y0, x0 + w, y0 + h), doors=doors, tick=r[a + 2], b23=r[a + 23],
                          nobj=r[a + 29], nblocks=r[a + 31], regions=regions)
        return out

    def roomlist(self, s):
        """the type-5 list of room s: object ids (0 entries dropped; id 0 is the hero / padding)"""
        a = self.res(5, s); rm = self.res(3, s)
        if a is None or rm is None: return []
        n = self.ram[rm + 29]
        return [u16(self.ram, a + 2 * i) for i in range(n + 1)]

    # ---- flags / doors (type 4)
    def flag(self, n):
        a = self.res(4, n)
        if a is None: return None
        r = self.ram
        return dict(addr=a, x=r[a], y=r[a + 1], word=u16(r, a + 2), b4=r[a + 4], b5=r[a + 5], b6=r[a + 6], b7=r[a + 7])
    def flags(self):
        idx, dat, cnt = self.tab[4]
        return {n: self.flag(n) for n in range(cnt) if self.res(4, n) is not None}

    # ---- the type-8 list (rucksack): records [object id][template idx], 4 bytes each from the data base, count byte 2438(A5)
    def rucksack(self):
        idx, dat, cnt = self.tab[8]
        n = self.ram[self.a5 + 2438]
        return n, [(u16(self.ram, dat + 4 * i), u16(self.ram, dat + 4 * i + 2)) for i in range(n)]

    def var(self, n): return self.ram[self.a5 + VARBASE + n]
    def cur_room(self): return u16(self.ram, self.a5 + 1166)


def typed(v, args):
    """printed args of vd.parse -> ints.  'o' kinds: '#N' decimal (<0x8000), 'actor' (0xffff), '#hex' otherwise."""
    ops = vd.VERBS[v][0]
    out = []
    if ops in ('IF', 'IFn'):
        return [int(a, 16) for a in args if not a.startswith('len')]
    if ops in ('V', 'Vb'):
        off = int(args[0].split('A5+')[1]); byte = args[0].startswith('byte')
        val = int(args[1], 16)
        return [off, val, byte] + ([int(args[2].split()[1])] if ops == 'Vb' else [])
    for k, a in zip(ops, args):
        if k == 'o':
            if a == 'actor': out.append(0xffff)
            else:
                d = int(a[1:])
                out.append(d if d < 1000 else int(a[1:], 16))
        else:
            out.append(int(a, 16))
    return out


class Block:
    """owner (object id or room slot), event, keep bit, gate bytes and the verb rows.  A row is
    (depth, verb, typed args, name, ctx); ctx = tuple of enclosing IFs, each (verb, n, conds, 'then'|'else') where conds are the
    COND verbs that precede the IF at its depth (the counter 2270(A5) the IF tests)."""
    __slots__ = ('kind', 'owner', 'idx', 'start', 'event', 'keep', 'gate', 'rows')

    def __init__(self, kind, owner, idx, start, e, rows):
        self.kind, self.owner, self.idx, self.start = kind, owner, idx, start
        self.event = e & 0x7f; self.keep = bool(e & 0x80)
        self.gate = [int(x, 16) for x in rows[0][2]]
        out = []; chain = []; last_if = {}
        for d, v, args, name in rows[1:]:
            if v < 0: continue
            ta = typed(v, args)
            del chain[d:]
            out.append((d, v, ta, name, tuple(chain)))
            if v in IFVERBS:
                n = ta[0] if vd.VERBS[v][0] == 'IFn' else None
                desc = (v, n, self._conds_before(out, d), 'then')
                last_if[d] = desc; chain.append(desc)
            elif v == 15 and d in last_if:
                p = last_if[d]; chain.append((p[0], p[1], p[2], 'else'))
        self.rows = out

    @staticmethod
    def _conds_before(out, d):
        c = []
        for dd, v, ta, name, ctx in reversed(out[:-1]):
            if dd != d or v not in CONDS: break
            c.append((v, tuple(ta)))
        return tuple(reversed(c))


def load_blocks(snap):
    """all object blocks (+$10 list only; see object3_artifact) and room blocks of a snapshot -> list[Block]"""
    out = []
    per = collections.defaultdict(int)
    skipped = []
    for oid, start, e, body in vd.collect(snap.path):
        if start != 0x10:
            skipped.append((oid, start, e, body)); continue
        rows = vd.decode_block(e, body)
        out.append(Block('obj', oid, per[oid], start, e, rows)); per[oid] += 1
    rrows, problems, nrooms = rb.room_blocks(snap.path)
    perr = collections.defaultdict(int)
    for slot, e, body, off in rrows:
        g = vd.GATE.get(e & 0x7f, 0)
        rows = [(0, -1, ['%02x' % b for b in body[:g]], 'GATE')]
        vd.parse(body, g, len(body), 0x17, rows)
        out.append(Block('room', slot, perr[slot], off, e, rows)); perr[slot] += 1
    return out, skipped


def object3_artifact(snap, skipped):
    """Proof that the `+$20` object hits of verb_decode.collect() are the NEXT record's own `+$10` list read through a 16-byte
    template: for each skipped (oid, 0x20, ...) find the object whose record address is exactly record(oid)+0x10 and compare
    its +$10 blocks.  Returns [(oid, neighbour, n_blocks, identical, rec_len, cnt_byte11)]."""
    res = []
    byaddr = {snap.res(6, i): i for i in snap.obj_ids()}
    got = collections.defaultdict(list)
    for oid, start, e, body in skipped: got[oid].append((e, body))
    for oid, lst in got.items():
        a = snap.res(6, oid)
        nb = byaddr.get(a + 0x10)
        same = None
        if nb is not None:
            nblocks = [(e, body) for o, s, e, body in vd.collect(snap.path) if o == nb and s == 0x10]
            same = nblocks == lst
        res.append((oid, nb, len(lst), same, snap.ram[a + 11], snap.ram[a + 31]))
    return res
