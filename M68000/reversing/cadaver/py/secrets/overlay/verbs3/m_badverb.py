"""m_badverb.py: a verb byte >= 94 reaches the dispatcher $011728 (add.w D0,D0; adda.w 0(A2,D0.w),A2; jmp (A2), A2 = $00ffba) with no range check: the word read
past the 94-entry table (the table is 188 bytes, $ffba-$10075) is the first code words of verb 0's handler ($010076...), used as a signed offset from $ffba.
Static: the computed targets for every byte 94..255; live (throwaway fork): a scratch script [94] and [96] under the consumer and what the machine does.
Run: cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/verbs3/m_badverb.py"""
from place_lib import *
import lib2

def run():
    h = H(SNAP0); r = h.r
    chk('bad verb: table size word at $00ffba = $%04x = 188 bytes = 94 words (verbs 0..93), the table ends at $%06x where the handler of verb zero starts' % (r.w(0xffba), 0xffba + r.w(0xffba)), r.w(0xffba) == 0xbc)
    tg = {}
    for v in range(94, 256):
        w = r.w(0xffba + 2 * v); sw = w - 65536 if w & 0x8000 else w; tg[v] = (0xffba + sw) & 0xffffff
    odd = [v for v, t in tg.items() if t & 1]
    chk('bad verb: targets of the 162 byte values 94..255 computed from the words at $ffba+2v: %d odd (address error on a 68000), %d inside $001000-$019100, e.g. 94 -> $%x, 95 -> $%x, 128 -> $%x' % (len(odd), sum(1 for t in tg.values() if 0x1000 <= t < 0x19100), tg[94], tg[95], tg[128]), len(tg) == 162)
    h.close()
    # live: the machine's reaction on a throwaway fork: run in 20,000-step chunks, record PC, stop when the emulator dies or settles
    for v in (94, 96):
        h = H(SNAP0); r = h.r; h.owner = 2
        set_body(h, [v]); inject5(h)
        t = tg[v]; log = []; died = None
        try:
            hh = r.hits(100000, 0xfe24, t)
            log.append(('hits fe24/target', hh.get(0xfe24, 0), hh.get(t, 0)))
            for k in range(8):
                r.cmd('s 20000'); log.append(hex(r.pc()))
        except RuntimeError as e:
            died = str(e)
            try: r.p.wait(timeout=5)
            except Exception: pass
        print('  v=%d target $%x (%s): %s died=%s returncode=%s stderr tail %s' % (v, t, 'odd' if t & 1 else 'even', log, died, r.p.returncode, [l for l in r.err if 'xception' in l or 'nhandled' in l or 'Illegal' in l or 'illegal' in l][:2]))
        chk('live[bad verb %d] scratch [%d] under the consumer: block entered (hits $fe24 = %s), target $%x %s; then %s' % (v, v, log[0][1] if log and isinstance(log[0], tuple) else None, t, 'entered %s times' % (log[0][2] if log and isinstance(log[0], tuple) else '?'), 'the emulator process died: ' + died if died else 'PC samples %s' % log[1:]),
            bool(log) and isinstance(log[0], tuple) and log[0][1] == 1 or bool(died))
        h.close()

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
