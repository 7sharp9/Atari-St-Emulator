"""h.py: shared harness for the verb-effect proofs (agent B, 80th pass).  Copy of the callcap-on-scratch-script pattern of
verb_effects_callcap.py plus resolvers for the resource types and an annotated memory delta."""
import sys, os, re
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
TMP = ROOT + '/scratchpad/cadaver/secrets_out/verbs2'
os.chdir(ROOT)
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay')
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets')
from ov import *          # Repl, A5, wb, ww, wl, a5
BUF = 0x7f000
SNAP0 = 'scratchpad/cadaver/gameplay_empire.snap'
SNAP1 = 'scratchpad/cadaver/level1_loaded.snap'


class H:
    def __init__(self, snap=SNAP0):
        self.snap = snap
        self.r = Repl(snap)
        r = self.r
        self.tab = [0xffba + int.from_bytes(r.mem(0xffba + 2 * i, 2), 'big') for i in range(94)]
        self.desc = r.l(A5 + 96)
        self._load_static()

    def close(self): self.r.close()

    # ---- resource resolvers (type rows are 18 bytes at (A5)+96; entry = index_table[id] long, low 17 bits = offset).
    # The index tables and row descriptors are static, so they are read once from the snapshot file.
    def _load_static(self):
        s = open(self.snap, 'rb').read(); off = 5 + 19 * 4 + 2
        self.ram = s[off + 4:off + 4 + 0x100000]
        u32 = lambda a: int.from_bytes(self.ram[a:a + 4], 'big')
        u16 = lambda a: int.from_bytes(self.ram[a:a + 2], 'big')
        self.rows = {}
        for t in range(10):
            row = self.desc + 0x12 * t
            self.rows[t] = (u32(row), u32(row + 4), u16(row + 16))
        self.spans = {}
        for t, (idx, dat, cnt) in self.rows.items():
            lst = []
            for i in range(min(cnt, 1000)):
                e = u32(idx + 4 * i)
                if e >> 16: lst.append((e & 0x1ffff, i))
            self.spans[t] = sorted(lst)
    def row(self, t): return self.desc + 0x12 * t
    def res(self, t, i):
        idx, dat, cnt = self.rows[t]
        e = int.from_bytes(self.ram[idx + 4 * i:idx + 4 * i + 4], 'big')
        if (e >> 16) == 0: return None
        return dat + (e & 0x1ffff)
    def obj(self, oid): return self.res(6, oid)
    def flag_rec(self, n): return self.res(4, n)
    def t8(self): return self.row(8)

    # ---- poking
    def poke(self, addr, data):
        for i, x in enumerate(data): wb(self.r, addr + i, x)
    def poke_a5(self, off, data): self.poke(A5 + off, data if isinstance(data, (bytes, bytearray)) else bytes(data))
    def put_script(self, script):
        s = (bytes(script) + bytes([0x17] * 24))[:max(24, len(script) + 4)]
        s += bytes(-len(s) % 4)
        for i in range(0, len(s), 4): self.r.cmd('w %x %s' % (BUF + i, s[i:i + 4].hex()))

    def call(self, verb, script, cap=300000, regs='A1=%x A4=7f100' % BUF):
        """callcap the verb handler with A1 -> script (result via the JSON out file, so the 4096-line print cap does not truncate);
        returns dict(ret, da1, delta {addr:(old,new)}, out, sp, thrown)"""
        import json
        self.put_script(script)
        path = TMP + '/cc_%d.json' % os.getpid()
        if os.path.exists(path): os.remove(path)
        out = self.r.cmd('callcap %x %d %s %s' % (self.tab[verb] if isinstance(verb, int) and verb < 94 else verb, cap, path, regs))
        d = {'ret': any('returned' in l for l in out), 'out': out, 'thrown': [l for l in out if 'THREW' in l], 'delta': {}, 'da1': None}
        j = json.load(open(path)); os.remove(path)
        sp = j['entrySP']; d['sp'] = sp
        d['da1'] = j['regN'][9] - BUF
        d['regN'] = j['regN']; d['reg0'] = j['reg0']; d['steps'] = j['steps']
        d['delta'] = {a: (o, n) for a, o, n in j['mem'] if not (sp - 0x1000 <= a < sp + 0x20)}
        return d

    # ---- annotation of an address
    def where(self, a):
        import bisect
        if A5 <= a < A5 + 0x1400: return '(A5)%+d' % (a - A5)
        if A5 - 0x80 <= a < A5: return 'stack'
        if not hasattr(self, '_regions'):
            ds = sorted(set(d for (i, d, c) in self.rows.values()))
            reg = []
            for t, (idx, dat, cnt) in self.rows.items():
                nxt = [d for d in ds if d > dat]
                end = nxt[0] if nxt else dat + 0x1000
                reg.append((dat, end, 'd', t)); reg.append((idx, idx + 4 * cnt, 'i', t))
            self._regions = sorted(reg)
        for (lo, hi, k, t) in self._regions:
            if lo <= a < hi:
                if k == 'i': return 'idx%d[%d]+%d' % (t, (a - lo) // 4, (a - lo) % 4)
                offs = self.spans[t]
                j = bisect.bisect_right(offs, (a - lo, 10**9)) - 1
                if j >= 0: return 't%d/id%d+%d' % (t, offs[j][1], a - lo - offs[j][0])
                return 't%d/data+%d' % (t, a - lo)
        return '$%06x' % a
    def structural(self, delta):
        """(state_items, other_count): state_items = sorted (where, old, new) for addresses in A5 (>=0) or the resource tables"""
        st, oth = [], 0
        for a, (o, n) in sorted(delta.items()):
            w = self.where(a)
            if w[0] == '$' or w == 'stack': oth += 1
            else: st.append((w, o, n))
        return st, oth
    def fmt_delta(self, d, maxn=60):
        rows = sorted(d['delta'].items())
        # merge into runs
        out = []
        for a, (o, n) in rows[:maxn]:
            out.append('%s %02x->%02x' % (self.where(a), o, n))
        if len(rows) > maxn: out.append('... +%d more' % (len(rows) - maxn))
        return '; '.join(out)


# ------------------------------------------------------------------------------------------------------------------
# "Real" runs: overwrite the body of object 2's event-5 block with a scratch script, inject event 5 into the ring queue and
# let the real consumer $00fdbc run it inside the live game (interrupts on).  A control run with a body of just $17 gives the
# noise mask (addresses the running game changes by itself).
import numpy as np
OWNER = 2

def ram_of(path):
    s = open(path, 'rb').read(); off = 5 + 19 * 4 + 2
    return np.frombuffer(s[off + 4:off + 4 + 0x100000], dtype=np.uint8)

_snapn = [0]
def snap_ram(h, tag='x'):
    _snapn[0] += 1
    p = TMP + '/tmp_%s_%d_%d.snap' % (tag, os.getpid(), _snapn[0])
    h.r.cmd('snap ' + p)
    a = ram_of(p); os.remove(p); return a

def owner_block(h):
    a = h.obj(getattr(h, 'owner', OWNER))
    b = h.r.mem(a + 0x10, 0x60)
    # find event-5 block: [len][0x85|0x05]
    return a + 0x10, b[0], b[1]

def set_body(h, script):
    """rewrite object 2's first block: [len][event|$80][script...][$17 pad]; len unchanged"""
    base, ln, ev = owner_block(h)
    assert ev & 0x7f == 5, (ln, ev)
    body = bytes(script) + bytes([0x17] * 64)
    body = body[:ln - 2]
    h.poke(base + 1, bytes([ev | 0x80]) + body)
    return ln

def inject5(h, oid=None, word=0, opcode=5):
    """append [opcode][rec(oid)][word] to the ring-304 queue: entry at the write pointer 304(A5), pointer += 8, count 1154(A5) += 1"""
    r = h.r
    oid = oid if oid is not None else getattr(h, 'owner', OWNER)
    w = r.l(A5 + 304)
    rec = h.obj(oid)
    r.cmd('w %x %08x' % (w, (opcode << 16) | (rec >> 16)))
    r.cmd('w %x %08x' % (w + 4, ((rec & 0xffff) << 16) | word))
    r.cmd('w %x %08x' % (A5 + 304, w + 8))
    ww(r, A5 + 1154, r.w(A5 + 1154) + 1)

def real(h, script, steps=150000, rec_hits=()):
    """run `script` for real in h's live game; returns dict(diff={addr:(old,new)}, hits)"""
    set_body(h, script)
    before = snap_ram(h)
    inject5(h)
    hits = h.r.hits(steps, 0xfe24, *rec_hits)
    after = snap_ram(h)
    idx = np.nonzero(before != after)[0]
    return {'diff': {int(i): (int(before[i]), int(after[i])) for i in idx}, 'hits': hits, 'pc': h.r.pc()}

def control(h, steps=150000):
    set_body(h, [])
    before = snap_ram(h)
    inject5(h)
    hits = h.r.hits(steps, 0xfe24)
    after = snap_ram(h)
    idx = np.nonzero(before != after)[0]
    return {int(i): (int(before[i]), int(after[i])) for i in idx}, hits

def sub_noise(diff, noise):
    return {a: v for a, v in diff.items() if a not in noise}


def summ(h, delta, maxn=30):
    """compact description of a memory delta: list of strings.  type-5 room-list compaction (index offsets shifted, data moved)
    is collapsed into one item."""
    st, oth = h.structural(delta)
    items = []; idx5 = []; t5 = 0; rest = []
    for w, o, n in st:
        if w.startswith('idx5['): idx5.append(w)
        elif w.startswith('t5/'): t5 += 1
        else: rest.append('%s %02x>%02x' % (w, o, n))
    # merge adjacent bytes of the same record/word for readability
    out = rest[:maxn] + (['...+%d' % (len(rest) - maxn)] if len(rest) > maxn else [])
    if idx5 or t5: out.append('[room-list compaction: %d idx5 bytes, %d t5 data bytes]' % (len(idx5), t5))
    if oth: out.append('[%d bytes elsewhere (screen/redraw buffers, no table)]' % oth)
    return out


def inject_run(h, oid, opcode, word=0, steps=150000, hitaddrs=()):
    """inject [opcode][rec(oid)][word] and run `steps`; returns (diff {addr:(old,new)}, hits)"""
    before = snap_ram(h)
    inject5(h, oid, word, opcode)
    hits = h.r.hits(steps, 0xfe24, *hitaddrs)
    after = snap_ram(h)
    idx = np.nonzero(before != after)[0]
    return {int(i): (int(before[i]), int(after[i])) for i in idx}, hits

def noise_for(snap, steps=150000, opcode=None):
    """noise mask from a control run in a fresh REPL (no event injected)"""
    h = H(snap)
    before = snap_ram(h)
    h.r.hits(steps, 0xfe24)
    after = snap_ram(h)
    idx = np.nonzero(before != after)[0]
    h.close()
    return set(int(i) for i in idx)
