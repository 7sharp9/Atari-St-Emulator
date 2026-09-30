"""dead_counter.py - the unreferenced routine $e74a (keypad '+' $4e / keypad '-' $4a adjust -8300(A4) and draw it as 4 decimal digits
through $e790/thunk 600): prove it is functional but unreachable.  On the race snapshot poke the keypad-plus cell to 'pressed' ($03) and
callcap $e74a: -8300(A4) goes 877 -> 878 and digit glyph blits are issued; then the same call with no key: unchanged."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
def setbyte(r, addr, v):
    a = addr & ~3
    cur = bytearray(r.mem(a, 4)); cur[addr & 3] = v
    r.cmd('w %x %s' % (a, bytes(cur).hex()))
for tag, plus, minus in (('no key', 0, 0), ('keypad + held', 3, 0), ('keypad - held', 0, 3)):
    r = R(sscfg.SNAP_RACE)
    setbyte(r, sscfg.A4 - 4802 + 0x4e, plus); setbyte(r, sscfg.A4 - 4802 + 0x4a, minus)
    v0 = r.g16(-8300)
    cj = os.path.join(AGENT, 'tmp', 'cce74a.json')
    out, g = r.cmd('callcap e74a 3000000 %s' % cj)
    j = json.load(open(cj))
    v1 = None
    for a, o, n in j['mem']:
        pass
    # value after = memory delta at A4-8300
    newv = {a: n for a, o, n in j['mem']}
    hi = newv.get(sscfg.A4 - 8300); lo = newv.get(sscfg.A4 - 8299)
    v1 = ((hi << 8) | lo) if hi is not None and lo is not None else (v0 if hi is None and lo is None else None)
    # partial change only one byte changes (e.g. 0x36d -> 0x36e)
    if v1 is None:
        b0 = r.mem(sscfg.A4 - 8300, 2); b = bytearray(b0)
        if hi is not None: b[0] = hi
        if lo is not None: b[1] = lo
        v1 = int.from_bytes(b, 'big')
    scr = sum(1 for a in newv if 0xf8000 <= a < 0xf8000 + 32000 or 0x21100 <= a < 0x21100 + 32000)
    print('%-14s -8300(A4): %d -> %d ; screen bytes written by the digit drawer: %d' % (tag, v0, v1, scr))
    r.close()
