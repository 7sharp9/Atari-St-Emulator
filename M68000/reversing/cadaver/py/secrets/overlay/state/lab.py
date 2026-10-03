"""lab.py: shared helpers for the live state experiments (all read-only on the repo; every run resumes a snapshot with the existing DLL, ATARI_NOTRACE=1 via Repl).
rec_of(r, id)      live type-6 record address (the heap compacts when objects are freed, so never cache it)
set_block(r, id, event, body)  rewrite the body of the object's first script block for `event` ($80 keep bit ignored) with a scratch script (block length unchanged, padded with $17); returns the old body
fire(r, id, event, word=0)     append a ring-304 entry [event][record][word] at the write pointer 304(A5), +8, 1154(A5)++ (the consumer $fdbc runs it after the next main-loop pass)
passes(r, n)       n main-loop passes (each = `s 1` then `u af10`)
sprites(r)         {object id: sprite entry dict} for the live sprite array
snap_png(r, name)  render the live screen to PNG via tools/snap_render.py and return a numpy array"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from live import *
import numpy as np
sys.path.insert(0, ROOT + '/tools')
TMP = OUTDIR + '/tmp'
os.makedirs(TMP, exist_ok=True)

def rec_of(r, oid):
    row = r.l(A5 + 96) + 0x12 * 6
    idx, dat = r.l(row), r.l(row + 4)
    e = r.l(idx + 4 * oid)
    return None if (e >> 16) == 0 else dat + (e & 0x1ffff)

def blocks(r, rec):
    n = r.mem(rec + 11, 1)[0]; p = rec + 0x10; out = []
    for _ in range(n):
        ln = r.mem(p, 1)[0]; out.append((p, ln, r.mem(p + 1, 1)[0])); p += ln
    return out

GATE_LEN = {1: 1, 12: 1, 13: 1, 15: 1, 17: 1, 19: 1, 20: 1, 24: 1, 4: 2, 9: 2, 10: 2, 18: 2, 26: 2}   # operand bytes of the event gates (secrets.md "Gate routines")
def set_block(r, oid, event, body):
    """rewrite the verb bytes of the object's first block for `event` with `body` (the gate operand bytes are kept); returns the gate word to put in the ring entry's word field"""
    rec = rec_of(r, oid)
    for p, ln, ev in blocks(r, rec):
        if ev & 0x7f == event:
            g = GATE_LEN.get(event, 0)
            assert len(body) + 3 + g <= ln, 'script of %d bytes does not fit block of %d (gate %d)' % (len(body), ln, g)
            gate = bytes(r.mem(p + 2, g)) if g else b''
            wb(r, p + 1, (event | 0x80))                            # keep bit: a non-keep block is spent ($ff) after its first run ($00fe3e)
            new = bytes(body) + bytes([0x17] * (ln - 2 - g - len(body)))
            for i, bb in enumerate(new): wb(r, p + 2 + g + i, bb)
            return int.from_bytes(gate, 'big') if g else 0
    raise KeyError('no block for event %d on object %d' % (event, oid))

def fire(r, oid, event, word=0, rec=None):
    rec = rec or rec_of(r, oid)
    wp = r.l(A5 + 304); n = r.w(A5 + 1154)
    r.cmd('w %x %04x%04x' % (wp, event, rec >> 16), 'w %x %04x%04x' % (wp + 4, rec & 0xffff, word))
    r.cmd('w %x %08x' % (A5 + 304, wp + 8)); ww(r, A5 + 1154, n + 1)

def passes(r, n=1):
    for _ in range(n):
        r.cmd('s 1')
        o = r.cmd('u af10 400000')
        if any('gave up' in l for l in o): raise RuntimeError('main loop not reached')

def sprites(r):
    return {o['id']: o for o in objs(r)}

def snap_png(r, name):
    import snap_render
    from PIL import Image
    p = TMP + '/%s_%d.snap' % (name, os.getpid())
    r.snap(p); png = TMP + '/%s.png' % name
    snap_render.render(p, png); os.remove(p)
    return np.array(Image.open(png).convert('RGB'))

def counters(r):
    return dict(dyn=r.w(A5 + 1148), stat=r.w(A5 + 1150), total=r.w(A5 + 1152))

def room(r): return r.w(A5 + 1166)

def callcap(r, addr, regs='', steps=300000):
    """callcap the subroutine at addr from the current state (registers preset in hex as 'D0=28 A1=7120c'); returns dict(ret, regN(list of 16 after), delta {addr: (old, new)}, steps)"""
    import json
    path = TMP + '/cc_%d.json' % os.getpid()
    if os.path.exists(path): os.remove(path)
    out = r.cmd('callcap %x %d %s %s' % (addr, steps, path, regs))
    j = json.load(open(path)); os.remove(path)
    sp = j['entrySP']
    return dict(ret=any('returned' in l for l in out), out=out, regN=j['regN'], reg0=j['reg0'], steps=j['steps'],
                delta={a: (o, n) for a, o, n in j['mem'] if not (sp - 0x1000 <= a < sp + 0x20)})

def pick_owner(r, need=3, exclude=()):
    """a live object with a script block big enough for `need` body bytes (plus its gate operand): returns (id, event)"""
    for oid in sorted(sprites(r)):
        if oid in exclude: continue
        rec = rec_of(r, oid)
        for p, ln, ev in blocks(r, rec):
            if ln >= need + 3 + GATE_LEN.get(ev & 0x7f, 0): return oid, ev & 0x7f
    raise RuntimeError('no owner')
