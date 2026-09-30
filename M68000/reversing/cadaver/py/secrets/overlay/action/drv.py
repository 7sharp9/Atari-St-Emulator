"""drv.py: shared helpers for the 80th-pass Task A drivers (copy of what Repl gives, plus joystick/key holds and state dumps)."""
import sys, os
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
os.chdir(ROOT)
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets')
from repl import Repl, A5
OUT = ROOT + '/scratchpad/cadaver/secrets_out/action/'
START = 'scratchpad/cadaver/gameplay_empire.snap'

# push sites (address of the `addq.w #1,1154(A5)` after the queue write) -> event
PUSH = {0xa418: 16, 0xa486: 5, 0xa59c: 5, 0xa5d2: 5, 0xa6f4: 18, 0xa72e: 27, 0xa7a4: 26, 0xa7ce: 5, 0xa184: 0}
PUSHNAME = {0xa418: 'ex16', 0xa486: 'use5a', 0xa59c: 'use5b', 0xa5d2: 'use5c', 0xa6f4: 'pick18', 0xa72e: 'sel27', 0xa7a4: 'sel26', 0xa7ce: 'use5d', 0xa184: 'take0'}

def joy(r, bits):
    """joystick port 1 (header $ff) state byte; bits 1 up 2 down 4 left 8 right 0x80 fire; persists until changed"""
    r.cmd(f'kbd ff {bits:02x}', 's 300')

def pos(r):
    return tuple(r.mem(0x38338, 4))  # player bbox [x_lead,y_lead,x_trail,y_trail]

def a5w(r, off): return r.a5(off, 2).hex()
def state(r):
    return dict(sel=r.a5(1262,2).hex(), front=r.a5(2128,2).hex(), fcls=r.a5(2476,1).hex(), cnt=r.a5(2438,1).hex(),
                q=r.a5(1154,2).hex(), dir=r.a5(2273,1).hex(), pos=pos(r))

import re
_ASM = None
def instr_addrs(lo, hi):
    global _ASM
    if _ASM is None:
        _ASM = []
        for l in open(OUT + 'lo.asm'):
            m = re.match(r'\s+\$([0-9a-f]{6}):', l)
            if m: _ASM.append(int(m.group(1), 16))
    return [a for a in _ASM if lo <= a < hi]

def cover(r, steps, ranges, extra=()):
    """run `steps` steps counting hits on every instruction start in ranges; returns [(first_step, addr, count)] sorted by first hit"""
    addrs = sorted(set(a for lo, hi in ranges for a in instr_addrs(lo, hi)) | set(extra))
    out = r.cmd(f'hits {steps} ' + ' '.join('%x' % a for a in addrs)); r.steps += steps
    res = []
    for l in out:
        t = l.split()
        if len(t) >= 6 and t[0].startswith('$') and int(t[1]):
            res.append((int(t[3]), int(t[0][1:], 16), int(t[1])))
    return sorted(res)

# ---- panel driver -------------------------------------------------------------------------------------------------
DISPATCH = {0: 0xa134, 1: 0xa1e0, 2: 0xa136, 3: 0xa494, 4: 0xa43c, 5: 0xa1c6, 6: 0xa134, 7: 0xa448, 8: 0xa292, 9: 0xa5c0,
            0xa: 0xa66a, 0xb: 0xa3d0, 0xc: 0xa682, 0xd: 0xa70e, 0xe: 0xa7b4, 0xf: 0xa782}   # $a0ac table resolved: icon id -> handler
KEYSITES = sorted(set(list(PUSH) + list(DISPATCH.values()) + [0xa08c, 0x9440, 0x9c82, 0x9682, 0xc42a, 0xc30e, 0xc3d4, 0xa748, 0xa73a,
                                                                 0xa14a, 0x6cce, 0xfdbc, 0xfe24, 0xfe30, 0xfe5a, 0x6f28, 0xa6a6, 0x9724, 0xa426, 0xa3fa, 0xa19e, 0xf44a, 0x6e70, 0x97b4, 0x6cb0, 0x6d10]))
class Tally:
    def __init__(self, r): self.r = r; self.tot = {}
    def run(self, n, sites=KEYSITES):
        for k, v in self.r.hits(n, *sites).items(): self.tot[k] = self.tot.get(k, 0) + v
    def joy(self, bits):
        """joystick packet, then the 300 settle steps counted in the tally (a bare joy() hides them from `hits`: the consumer starts ~300 steps after a fire release)"""
        self.r.cmd(f'kbd ff {bits:02x}'); self.run(300)
    def show(self): return {hex(k): v for k, v in sorted(self.tot.items()) if v}
    def reset(self): self.tot = {}

def type8(r):
    """(count, index words nonzero, data records) of the type-8 list: A0 = 96(A5) + 8*$12; A1 = (A0) index array (64 words, 4-byte
    stride words: [flag.w][ofs.w]), A2 = 4(A0) 4-byte data records [id][+2]"""
    a0 = r.l(A5 + 96) + 8 * 0x12
    idx, dat = r.l(a0), r.l(a0 + 4)
    n = r.a5(2438, 1)[0]
    recs = [(r.w(dat + 4 * i), r.w(dat + 4 * i + 2)) for i in range(n + 2)]
    return dict(desc=hex(a0), index=hex(idx), data=hex(dat), count=n, recs=recs, idxwords=r.mem(idx, 16).hex())

def open_panel(r, t, hold=40000):
    """near an object: fire hold (opens the icon-choice loop at $9c82, which first waits for the release), release"""
    t.joy(0x80); t.run(hold); t.joy(0x00); t.run(20000)

def pulse(r, t, bits, hold=22000, settle=45000):
    t.joy(bits); t.run(hold); t.joy(0); t.run(settle)
def cur_icon(r):
    """icon id under the cursor in the object panel (2478 = row, 2472 = slot, 2303 = icon count): layout byte at $6180+row*64+count*8+slot is the box; box 6 = cancel"""
    row, slot, cnt = r.a5(2478, 1)[0], r.a5(2472, 1)[0], r.a5(2303, 1)[0]
    box = r.b(0x6180 + row * 64 + cnt * 8 + slot)
    return (6 if box == 6 else r.b(0x5ff6 + box)), box
def pick_icon_id(r, t, want, hold=40000):
    """navigate the object panel to icon id `want` (right/down pulses), confirm with fire.  Returns the path taken."""
    path = []
    for _ in range(12):
        cur, box = cur_icon(r)
        if cur == want: break
        # try right first (wraps within the row); after 3 rights without success switch row with down
        pulse(r, t, RIGHT if len(path) % 3 != 2 else DOWN); path.append('R' if len(path) % 3 != 2 else 'D')
    cur, box = cur_icon(r)
    assert cur == want, (cur, box, path)
    t.joy(FIRE); t.run(hold); t.joy(0); t.run(70000)
    return path
def cancel_panel(r, t):
    r.cmd('kbd 39'); t.run(40000); r.cmd('kbd b9'); t.run(60000)

UP, DOWN, LEFT, RIGHT, FIRE = 1, 2, 4, 8, 0x80
def walk(r, bits, max_steps=3000000, chunk=50000, until=None, quiet=True):
    """hold joystick `bits`; stop when the hero bbox stops changing over a chunk, or `until(pos)` is true, or the budget is spent"""
    joy(r, bits)
    last = pos(r); n = 0; stall = 0
    while n < max_steps:
        r.cmd(f's {chunk}'); n += chunk
        p = pos(r)
        if until and until(p): break
        if p == last:
            stall += 1
            if stall >= 2: break
        else: stall = 0
        last = p
    joy(r, 0); r.cmd('s 30000')
    return pos(r)

def icons(r):
    """current icon list at $5ff6 up to the 0xff terminator"""
    m = r.mem(0x5ff6, 10); out = []
    for b in m:
        if b == 0xff: break
        out.append(b)
    return out
def tmpl_id(r, a): return r.w(a + 4)

QBASE = 0x39dbe
def watch_queue(r, n=200):
    """start a watch over the first 20 queue entries; call events(r) later"""
    r.err.clear(); r.cmd(f'watch {QBASE:x} {n}')
def idmap(r):
    """template pointer -> object id for every object in the room, read BEFORE the action (a DELETE verb compacts the resource block and moves later templates)"""
    base = int.from_bytes(r.a5(56,4),'big'); n = int.from_bytes(r.a5(1152,2),'big'); m = {}
    for i in range(n):
        e = r.mem(base+70*i, 70); t = int.from_bytes(e[10:14],'big')
        if 0x1000 < t < 0x7ffff: m[t] = r.w(t+4)
    return m
def events(r, clear=True, ids=None):
    """[(pc, opcode, obj_ptr, obj_id, entry_offset)] reconstructed from the watch lines (ring entries are 8 bytes: op.w ptr.l word.w)"""
    ent = {}
    order = []
    for l in list(r.err):
        m = re.match(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) Write(\w+) \$([0-9a-f]+) <- \$([0-9a-f]+)', l)
        if not m: continue
        step, pc, kind, addr, val = int(m.group(1)), int(m.group(2), 16), m.group(3), int(m.group(4), 16), int(m.group(5), 16)
        off = addr - QBASE; k = off // 8; f = off % 8
        e = ent.setdefault((k, step // 1), {})  # keyed by (slot, step) is too fine; group by consecutive writes below
        order.append((step, pc, k, f, val, kind))
    # group writes: an entry starts at f == 0 word write
    evs = []; cur = None
    for step, pc, k, f, val, kind in order:
        if f == 0:
            cur = dict(pc=pc, step=step, op=val, hi=None, lo=None, slot=k); evs.append(cur)
        elif cur is not None and cur['slot'] == k:
            if f == 2: cur['hi'] = val
            elif f == 4: cur['lo'] = val
            elif f == 6: cur['w'] = val
    out = []
    for e in evs:
        ptr = ((e['hi'] or 0) << 16) | (e['lo'] or 0)
        out.append((e['pc'], e['op'], ptr, (ids.get(ptr) if ids and ptr in ids else (ptr and r.w(ptr + 4))), e['slot'], e.get('w')))
    if clear: r.err.clear()
    return out
def fmt_events(evs): return ' | '.join(f'pc=${pc:06x} op={op:#x}({op & 0xff}) obj@${ptr:06x} id={oid}' + (f' w={w:#x}' if w is not None else '') for pc, op, ptr, oid, s, w in evs)

def probe(r, budget=120000):
    """fire held: if an object is in front the icon loop $9c82 is entered.  Returns (template id, icons) or None; the panel is then cancelled with Space."""
    joy(r, FIRE)
    out = r.cmd(f'bp 9c82 {budget}')
    hit = any('breakpoint' in l and 'hit' in l for l in out)
    if not hit:
        joy(r, 0); r.cmd('s 30000'); return None
    regs = ' '.join(r.cmd('r'))
    a6 = int(re.search(r'A6:([0-9a-f]{8})', regs).group(1), 16); a4 = int(re.search(r'A4:([0-9a-f]{8})', regs).group(1), 16)
    ic = icons(r)
    t = Tally(r)
    joy(r, 0); t.run(30000); cancel_panel(r, t)
    return tmpl_id(r, a6), ic, a6, r.b(a4 + 22), r.b(a4 + 23)

def tap(r, t, sc, hold=40000, after=90000):
    """real make, hold, break, settle (the key action runs after the break: $11898 waits for release first)"""
    r.cmd(f'kbd {sc:02x}'); t.run(hold); r.cmd(f'kbd {sc | 0x80:02x}'); t.run(after)
def ruck_panel(r, t, mode='space'):
    """open the rucksack item panel ($9682 -> $9724 -> $9c82).  space: straight to the icon panel of item 2122; return: the grid $97b4 first,
    confirm the highlighted item with fire, then the icon panel."""
    if mode == 'space': tap(r, t, 0x39)
    else:
        tap(r, t, 0x1c)
        t.joy(FIRE); t.run(40000); t.joy(0); t.run(90000)

# ---- reproducible start snapshots (natural joystick routes from gameplay_empire.snap / room2_tunnel_entry.snap) -------------
ROUTES = {'coin': (START, [RIGHT]), 'pick': (START, [RIGHT, UP, RIGHT, DOWN]), 'book': (START, [RIGHT, UP, DOWN]), 'boat': (START, [DOWN]),
          'barrel': (START, [DOWN, LEFT]), 'diary': (START, [DOWN, RIGHT]), 'tome': (START, [DOWN, RIGHT, UP, RIGHT]),
          'lever': ('scratchpad/cadaver/room2_tunnel_entry.snap', [LEFT])}
def ensure(name):
    """path of sv_<name>.snap, made on first use.  sv_held: pickaxe taken (icon 2 at the pickaxe); sv_held_lever: then UP (door to TUNNEL) and LEFT (lever in front)"""
    path = OUT + f'sv_{name}.snap'
    if os.path.exists(path): return path
    if name in ROUTES:
        start, legs = ROUTES[name]; r = Repl(start)
        for b in legs: walk(r, b)
        r.snap(path); r.close()
    else:
        r = Repl(ensure('pick')); t = Tally(r); open_panel(r, t); pick_icon_id(r, t, 2)
        if name == 'held_lever':
            for b in [UP, LEFT]: walk(r, b)
        r.snap(path); r.close()
    return path
