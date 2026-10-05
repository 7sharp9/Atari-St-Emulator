#!/usr/bin/env python3
"""Static decoder for the sequencer streams of effect songs (flag $5F = 0: raw-time mode, parsed by $E925/$E952) and the OKI starts they contain.
Effect-mode grammar (from $E952, E95E): byte < $80 duration (raw time units: each IRQ2 consumes $1B4 = 436 of a 16-bit count whose high byte is the
duration, i.e. 256/436 of an IRQ2 = 1.174 ms per unit);  $80-$8f note (pitch only, no key-on);  $90-$df opcode (table $E97A) with operands;  $a8 ends the channel.
Operand byte counts per opcode: OPLEN below = observed in the MAME traces (analyze_trace.py ops) and confirmed against the handler bodies.
usage: static_streams.py [id ...]     prints the decoded stream and its OKI starts (table entry n of oki1 for $cc, oki2 for $cb)"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import songs as S

OPLEN = {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 0, 6: 1, 7: 2, 8: 2, 9: 2, 10: 1, 11: 0, 12: 2, 13: 0, 14: 1, 15: 1, 16: 1, 17: 1, 18: 2,
         19: 2, 20: 2, 21: 2, 22: 0, 23: 0, 24: 0, 25: 2, 26: 2, 27: 2, 28: 2, 29: 3, 30: 0, 31: 0, 32: 0, 33: 0, 34: 1, 35: 1, 36: 1, 37: 1,
         38: 1, 39: 1, 40: 1, 41: 1, 42: 1, 43: 1, 44: 1, 45: 0, 46: 0, 47: 0, 48: 1, 58: 1, 59: 1, 60: 1, 61: 0, 62: 0, 63: 0, 64: 0,
         65: 1, 66: 1, 67: 1, 68: 1, 69: 1, 70: 1, 71: 2}
for i in range(49, 58): OPLEN[i] = 0
NAME = {0: 'rest', 3: 'octave', 4: 'vol', 7: 'patchptr', 8: 'tempo', 9: 'jump', 10: 'rep', 11: 'endrep', 12: 'call', 13: 'ret', 22: 'keyon', 23: 'keyoff', 24: 'END',
        29: 'ch3op', 59: 'oki2', 60: 'oki1', 61: 'oki2stop', 62: 'oki1stop', 66: 'patch'}

def decode(start, ch, limit=4000):
    """Expand one effect stream. Returns list of events (kind, value...) and flag 'loops' if an infinite jump was detected."""
    out = []; stack = []; pos = start; steps = 0; seen = set(); loops = False
    while steps < limit:
        steps += 1
        b = S.rb(pos)
        if b < 0x80:
            out.append(('dur', b)); pos += 1
        elif b < 0x90:
            out.append(('note', b & 0xf)); pos += 1
        else:
            idx = b - 0x90
            n = OPLEN.get(idx)
            if idx in (19, 20, 21) and ch >= 11: n = 1
            if n is None: out.append(('?op', b)); return out, loops
            args = [S.rb(pos + 1 + k) for k in range(n)]
            nm = NAME.get(idx, 'op%02x' % b)
            out.append((nm, *args))
            if idx == 24: return out, loops
            if idx == 9:
                tgt = args[0] | args[1] << 8
                if tgt <= pos:
                    loops = True; out.append(('LOOP-BACK', tgt)); return out, loops
                pos = tgt; continue
            if idx == 10:
                stack.append(['rep', pos + 2, args[0]]); pos += 2; continue
            if idx == 11:
                top = stack[-1]
                top[2] -= 1
                if top[2] > 0: pos = top[1]
                else: stack.pop(); pos += 1
                continue
            if idx == 12:
                stack.append(['call', pos + 3]); pos = args[0] | args[1] << 8; continue
            if idx == 13:
                top = stack.pop(); pos = top[1]; continue
            pos += 1 + n
    out.append(('LIMIT',)); return out, loops

def oki_starts(events):
    o1 = [e[1] for e in events if e[0] == 'oki1']
    o2 = [e[1] for e in events if e[0] == 'oki2']
    return o1, o2

if __name__ == '__main__':
    ids = [int(a, 16) for a in sys.argv[1:]] or range(1, S.MAXID + 1)
    for i in ids:
        p, h, chans, q = S.header(i)
        if h[2]: continue
        for ch, a in chans:
            ev, loops = decode(a, ch)
            o1, o2 = oki_starts(ev)
            print('%02x ch%d @%04x %s%s' % (i, ch, a, ' '.join('%s%s' % (e[0], ('(%s)' % ','.join('%02x' % x for x in e[1:])) if len(e) > 1 else '') for e in ev[:40]), ' ...' if len(ev) > 40 else ''))
            if o1 or o2: print('     OKI starts: oki1 table entries %s  oki2 table entries %s' % (o1, o2))
