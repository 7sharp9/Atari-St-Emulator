"""lib2.py: assertion helpers shared by verb_effects2.py sections."""
from h import *

OK = BAD = 0
LOG = []
TALLY = {}   # verb id -> [ok, bad]

def chk(label, cond, extra=''):
    global OK, BAD
    if cond: OK += 1
    else: BAD += 1
    import re as _re
    tags = set(int(x) for x in _re.findall(r'verb\s+(\d+)', label)) | set(int(x) for m in _re.findall(r'\[v([\d,]+)\]', label) for x in m.split(','))
    for t in tags:
        TALLY.setdefault(t, [0, 0])[0 if cond else 1] += 1
    line = '%-96s %s%s' % (label, 'ok' if cond else 'BAD', ('   ' + str(extra)) if (extra and not cond) else '')
    print(line); LOG.append(line)
    return cond

def after(h, d, addr, n):
    """the n bytes at addr after the call: live pre-state with the callcap delta applied"""
    cur = bytearray(h.r.mem(addr, n))
    for i in range(n):
        if addr + i in d['delta']: cur[i] = d['delta'][addr + i][1]
    return bytes(cur)

def afterw(h, d, addr): return int.from_bytes(after(h, d, addr, 2), 'big')
def afterl(h, d, addr): return int.from_bytes(after(h, d, addr, 4), 'big')
def afterb(h, d, addr): return after(h, d, addr, 1)[0]

def changed(h, d, prefix):
    """callcap delta items whose annotated location starts with prefix"""
    st, _ = h.structural(d['delta'])
    return [x for x in st if x[0].startswith(prefix)]

def rec_bytes(h, oid, n=24): return h.r.mem(h.obj(oid), n)

def tmpl_bytes(h, oid):
    t = int.from_bytes(h.ram[h.obj(oid) + 6:h.obj(oid) + 8], 'big')
    ta = h.res(2, t); return h.ram[ta:ta + 32]

def t5_list(h, room, d=None):
    """the room's type-5 object-id list (live, or after a callcap delta): returns (ids, size_bytes, offset)"""
    idx, dat, cnt = h.rows[5]
    ea = idx + 4 * room
    if d is None: e = h.r.l(ea)
    else: e = afterl(h, d, ea)
    size, off = e >> 16, e & 0x1ffff
    b = h.r.mem(dat + off, max(size, 2)) if d is None else after(h, d, dat + off, max(size, 2))
    return [int.from_bytes(b[i:i + 2], 'big') for i in range(0, size, 2)], size, off

def room_counts(h, room, d=None):
    rm = h.res(3, room)
    if d is None: b = h.r.mem(rm + 27, 3)
    else: b = after(h, d, rm + 27, 3)
    return b[0], b[1], b[2]        # +27 (bit0 objects), +28 (others), +29 (total)

def a5b(h, off, n=1, d=None):
    if d is None: return h.r.mem(A5 + off, n)
    return after(h, d, A5 + off, n)
def a5w(h, off, d=None): return int.from_bytes(a5b(h, off, 2, d), 'big')
def a5l(h, off, d=None): return int.from_bytes(a5b(h, off, 4, d), 'big')
