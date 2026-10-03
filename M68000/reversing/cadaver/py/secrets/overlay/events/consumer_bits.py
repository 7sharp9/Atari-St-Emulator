"""a3: consumer_bits.py -- the real queue consumer $00fdbc, fed with injected ring-304 entries in the live game (level1_loaded.snap), one fresh REPL per case.
Counts hits on the consumer's own branches: $fe0c (a block list is walked), $fe24 (block event byte equals the opcode low byte), $fe36 (the gate accepted),
$fe5a (a verb was dispatched), $fe74 (the object's list was empty), $ffa4 (event-8 native path), $fef2 (event 15/17 gate copies 384(A5) to 348(A5)).
Proves: (a) opcode bit 14 picks template +$20 / count byte 31, no bit 14 picks +$10 / count byte 11; (b) bit 15 makes the entry 12 bytes and the 4th longword lands in 384(A5)
(and, for events 15/17, in 348(A5) after the gate accepts); (c) event 8 never reaches a block list; (d) a block of event 2 matches but its gate rejects.
Usage (from M68000/): .venv/bin/python reversing/cadaver/py/secrets/overlay/events/consumer_bits.py   Expected: 'matched n of n'."""
import sys, os, struct
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
OUTDIR = os.environ.get('OUTDIR') or os.path.join(ROOT, 'scratchpad/cadaver/s91_events'); os.makedirs(OUTDIR, exist_ok=True)   # scratch output (callcap json, caches, scan listings)
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
import h as HH
from h import *
os.chdir(ROOT); HH.TMP = OUTDIR
A5 = HH.A5
SNAP1 = os.path.join(ROOT, 'scratchpad/cadaver/level1_loaded.snap')
SITES = [0xfdbc, 0xfe0c, 0xfe24, 0xfe36, 0xfe5a, 0xfe74, 0xffa4, 0xfef2]
NAMES = {0xfdbc: 'cons', 0xfe0c: 'list', 0xfe24: 'match', 0xfe36: 'gate_ok', 0xfe5a: 'verb', 0xfe74: 'empty/end', 0xffa4: 'ev8', 0xfef2: 'copy384'}

def push(h, entries):
    """append entries (opcode, ptr, word[, long4]) at the write pointer 304(A5); count 1154(A5) += n"""
    r = h.r
    w = r.l(A5 + 304); buf = b''
    for e in entries:
        buf += struct.pack('>HIH', e[0], e[1], e[2]) + (struct.pack('>I', e[3]) if len(e) > 3 else b'')
    assert len(buf) % 4 == 0
    for i in range(0, len(buf), 4): r.cmd('w %x %s' % (w + i, buf[i:i + 4].hex()))
    r.cmd('w %x %08x' % (A5 + 304, w + len(buf)))
    ww(r, A5 + 1154, r.w(A5 + 1154) + len(entries))

def run(h, entries, steps=60000):
    push(h, entries)
    hits = h.r.hits(steps, *SITES)
    return {NAMES[a]: hits.get(a, 0) for a in SITES}

cases = []
def case(label, entries_fn, expect, pre=None, post=None):
    cases.append((label, entries_fn, expect, pre, post))

# object records of level 1: id 4 carries two event-26 blocks at +$10 (gates $01d9, $02ab); id 3 is a 16-byte header-only record whose +$20 aliases id 4's +$10 list
case('op $001a obj 4 (list +$10), word $01d9: block matches, gate accepts, verbs run',
     lambda h: [(0x001a, h.obj(4), 0x01d9)], dict(match=1, gate_ok=1))
case('op $001a obj 4, word $02ab: both blocks match the event byte, the second gate accepts',
     lambda h: [(0x001a, h.obj(4), 0x02ab)], dict(match=2, gate_ok=1))
case('op $001a obj 4, word $9999: both blocks match the event byte, no gate accepts',
     lambda h: [(0x001a, h.obj(4), 0x9999)], dict(match=2, gate_ok=0, verb=0))
case('op $401a obj 4 (bit 14 -> +$20, count byte 31 = %s): nothing', lambda h: [(0x401a, h.obj(4), 0x01d9)], dict(match=0))
case('op $001a obj 3 (count byte 11 = 0, +$10 list empty): nothing',
     lambda h: [(0x001a, h.obj(3), 0x01d9)], dict(match=0, list=0))
case('op $401a obj 3 (bit 14: count byte 31 = 2 -> +$20 = obj 4\'s +$10 blocks): the alias runs',
     lambda h: [(0x401a, h.obj(3), 0x01d9)], dict(match=1, gate_ok=1))
# room records: blocks at +$20, count at byte 31; room 2 has an event-6 block, room 1 an event-15 and an event-24 block
case('op $4006 room 2 (bit 14 -> +$20): event-6 block runs',
     lambda h: [(0x4006, h.res(3, 2), 0)], dict(match=1, gate_ok=1))
case('op $0006 room 2 (no bit 14 -> +$10, count byte 11 of a room record): nothing',
     lambda h: [(0x0006, h.res(3, 2), 0)], dict(match=0))
case('op $4018 room 1 word $17 (event 24, gate $17): runs',
     lambda h: [(0x4018, h.res(3, 1), 0x17)], dict(match=1, gate_ok=1))
case('op $4018 room 1 word $16: gate rejects',
     lambda h: [(0x4018, h.res(3, 1), 0x16)], dict(match=1, gate_ok=0))
# bit 15: 12-byte entry; event 15 gate copies the 4th longword into 348(A5)
MARK = 0x00012345
case('op $c00f room 7 word $01, 4th long $%08x then op $4006 room 2: the 12-byte entry is parsed, 384(A5) = long, the next entry still runs' % MARK,
     lambda h: [(0xc00f, h.res(3, 7), 0x0001, MARK), (0x4006, h.res(3, 2), 0)], dict(match=2, gate_ok=2, copy384=1),
     post=lambda h: dict(l384=h.r.l(A5 + 384)))
case('op $400f room 7 word $01 (event 15 WITHOUT bit 15: 8-byte entry): gate accepts, 384(A5) not rewritten (stale)',
     lambda h: [(0x400f, h.res(3, 7), 0x0001)], dict(match=1, gate_ok=1, copy384=1),
     pre=lambda h: wl(h.r, A5 + 384, 0x00054321), post=lambda h: dict(l384=h.r.l(A5 + 384), l348=h.r.l(A5 + 348)))
# event 8: native banner path, never a block list
case('op $0008 obj 4: $ffa4 path, no block list walked', lambda h: [(0x0008, h.obj(4), 0)], dict(ev8=1, list=0, match=0))
case('op $4008 obj 4 (bit 14 set, low byte 8): the same native path', lambda h: [(0x4008, h.obj(4), 0)], dict(ev8=1, list=0, match=0))
# event 2: poke object 4's first block event byte $1a -> $02: matches, gate rejects
def poke_ev2(h):
    a = h.obj(4); wb(h.r, a + 0x11, 0x02)
case('event-2 block (event byte poked $1a -> $02 in obj 4\'s first block), op $0002 word $01d9: matches, gate rejects, no verb',
     lambda h: [(0x0002, h.obj(4), 0x01d9)], dict(match=1, gate_ok=0, verb=0), pre=poke_ev2)

if __name__ == '__main__':
    good = 0
    for label, efn, expect, pre, post in cases:
        h = HH.H(SNAP1)
        if pre: pre(h)
        if '%s' in label: label = label % h.ram[h.obj(4) + 31]
        got = run(h, efn(h))
        extra = post(h) if post else {}
        ok = all(got.get(k) == v for k, v in expect.items())
        if 'op $c00f' in label: ok = ok and extra['l384'] == MARK
        print('%-110s %s %s %s' % (label[:110], 'ok ' if ok else 'BAD', {k: v for k, v in got.items() if v or k in expect}, {k: '%08x' % v for k, v in extra.items()}))
        good += ok
        h.close()
    print('matched %d of %d' % (good, len(cases)))
