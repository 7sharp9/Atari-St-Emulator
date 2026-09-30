"""verb_lengths_callcap.py [snap]: measure every verb's operand length on the real interpreter.

For each entry of the verb table `$00ffba` the handler is called with `callcap` (register preset A1 = a scratch script
buffer at $7f000 filled with a benign pattern) and the delta of A1 at the return is the number of operand bytes the verb
consumed.  The result is compared with `verb_decode.VERBS`.  The IF verbs (14, 48, 58, 59) are given `[len=2][$16]` with
2270(A5) preset to make the condition true and, in a second run, false; the variable-length verbs 62-64 are tried with both
forms of the first word (bit 15 clear: a word operand, set: a byte operand).  A handler that never returns inside the step
cap is reported as 'no return': verb 15 is a fatal assert by design, verb 51 jumps into the level loader (its one-byte
operand is covered by the 212-block tiling of `verb_decode.py` and by `level_verb_live.py`), and verbs 8 and 75 call `$e172`, which
asserts unless the id is in the creature list at 396(A5), so the list is seeded with id $0090 first.  Expected: ok 99,
bad 0, no-return 2 (15, 51).

Run from M68000/: `uv run python reversing/cadaver/py/secrets/overlay/verb_lengths_callcap.py`."""
import sys, re
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
from verb_decode import VERBS, SIZE

snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
BUF = 0x7f000
r = Repl(snap)
tab = [0xffba + int.from_bytes(r.mem(0xffba + 2 * i, 2), 'big') for i in range(94)]
PAT = bytes([0x00, 0x90] * 8)   # id $0090 (144: the TUNNEL lever) read as a word, 0/144 as bytes


def measure(handler, script, presets=''):
    """returns (delta, returned)"""
    padded = (script + bytes([0x17] * 24))[:24]
    for i in range(0, 24, 4):
        r.cmd('w %x %s' % (BUF + i, padded[i:i + 4].hex()))
    if presets: r.cmd(presets)
    out = r.cmd('callcap %x 300000 - A1=%x A4=7f100' % (handler, BUF))
    ret = any('returned' in l for l in out)
    for l in out:
        m = re.search(r'A1 \$[0-9a-f]+->\$([0-9a-f]+)', l)
        if m: return int(m.group(1), 16) - BUF, ret     # regdelta shows the final A1; BUF is the preset
    return None, ret


def expect(v):
    ops = VERBS[v][0]
    if ops in ('IF', 'IFn', 'V', 'Vb'): return None
    return sum(SIZE[k] for k in ops)


ok = bad = norun = 0
for v in range(94):
    e = expect(v)
    if e is None: continue
    seed = 'w %x 00010090' % (A5 + 396) if v in (8, 75) else ''      # 8 and 75 unregister id $0090: it must be in the list
    d, ret = measure(tab[v], PAT, seed)
    if not ret:                                   # retry with object 12, which satisfies the class checks of verbs 11 and 12
        d, ret = measure(tab[v], bytes([0, 12] * 8))
    if not ret:
        norun += 1; print('verb %2d  $%06x  expect %d  no return in the step cap' % (v, tab[v], e)); continue
    flag = 'ok ' if d == e else 'BAD'
    if d == e: ok += 1
    else: bad += 1
    print('verb %2d  $%06x  expect %d  measured %d  %s  %s' % (v, tab[v], e, d, flag, VERBS[v][1]))

# IF verbs: [len=2][$16] (then part empty).  14 runs it when 2270 != 0, 48 when 2270 == 0, 58/59 take a count byte first.
A2270 = A5 + 2270
for v, script, setv, label in ((14, bytes([2, 0x16]), 1, 'cond true'), (14, bytes([2, 0x16]), 0, 'cond false'),
                               (48, bytes([2, 0x16]), 0, 'cond true'), (48, bytes([2, 0x16]), 1, 'cond false'),
                               (58, bytes([1, 2, 0x16]), 1, '==1 true'), (58, bytes([1, 2, 0x16]), 0, '==1 false'),
                               (59, bytes([1, 2, 0x16]), 0, '!=1 true'), (59, bytes([1, 2, 0x16]), 1, '!=1 false')):
    base = A2270 & ~1; cur = bytearray(r.mem(base, 4)); cur[A2270 - base] = setv
    d, ret = measure(tab[v], script, 'w %x %s' % (base, cur.hex()))
    n = len(script)
    flag = 'ok ' if (ret and d == n) else 'BAD'
    if ret and d == n: ok += 1
    else: bad += 1
    print('verb %2d  IF %-10s script %s  consumed %s (expect %d)  %s' % (v, label, script.hex(), d, n, flag))

# variable-length verbs: first word bit 15 clear -> word operand, set -> byte operand
for v, w1, exp, label in ((62, 0x0010, 4, 'word form'), (62, 0x8010, 3, 'byte form'), (63, 0x0010, 4, 'word form'), (63, 0x8010, 3, 'byte form'),
                          (64, 0x0010, 5, 'word form'), (64, 0x8010, 4, 'byte form')):
    s = bytes([w1 >> 8, w1 & 0xff, 0, 5, 0, 5])
    d, ret = measure(tab[v], s)
    flag = 'ok ' if (ret and d == exp) else 'BAD'
    if ret and d == exp: ok += 1
    else: bad += 1
    print('verb %2d  V %-9s consumed %s (expect %d)  %s' % (v, label, d, exp, flag))
print('ok %d  bad %d  no-return %d' % (ok, bad, norun))
r.close()
