#!/usr/bin/env python3
"""Latch values >= $80: effect of a PRE command on a following song/effect, from sweep logs (run_high.sh).
  hv_*: YM2151 TL (regs $60-$7f) data written during the song: master volume ($80-$9f)
  ht_*: key-on frames of the song: tempo offset ($d0-$ff)
  hf_*: YM2203 TL regs ($40-$4f) of an effect: FM master volume ($a0-$bf)
  ho1_*/ho2_*: OKI attenuation nibble of phrase starts: oki1 ($c8-$cf) / oki2 ($c0-$c7)"""
import sys, glob, os, collections, statistics
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import analyze_sweep as A

def blk(path):
    b = A.parse(path)
    return list(b.values())[0]

def tl(path, chip, lo, hi):
    b = blk(path)
    w = A.decode(b['ev'])
    vals = [v for f, c, r, v in w if c == chip and isinstance(r, int) and lo <= r < hi]
    return vals

def keyons(path):
    b = blk(path)
    base = b['send']
    w = A.decode(b['ev'])
    out = collections.defaultdict(list)
    for f, c, r, v in w:
        if c == 'ym2151' and r == 8 and v & 0x78: out[v & 7].append(f - base)
    return out

for pre in ('none', '80', '8f', '9f'):
    p = os.path.join(HERE, 'out', 'hv_0a_%s.log' % pre)
    if os.path.exists(p):
        v = tl(p, 'ym2151', 0x60, 0x80)
        # TL after the song's own patch loads: the per-note volume writes are the last writes of each channel group; use the multiset
        print('hv_0a_%-4s YM2151 TL writes %4d  max %3d  mean %.2f  distinct %d' % (pre, len(v), max(v) if v else -1, statistics.mean(v) if v else -1, len(set(v))))
print()
for pre in ('none', 'e0', 'd0', 'ff'):
    p = os.path.join(HERE, 'out', 'ht_0e_%s.log' % pre)
    if os.path.exists(p):
        k = keyons(p)
        ch = max(k, key=lambda c: len(k[c]))
        ks = k[ch]
        n = len(ks)
        span = ks[min(n, 12) - 1] - ks[0] if n > 1 else 0
        print('ht_0e_%-4s ch%d key-ons %3d  first %s  frames from 1st to 12th key-on: %d' % (pre, ch, n, ks[:6], span))
print()
for pre in ('none', 'a0', 'bf'):
    p = os.path.join(HERE, 'out', 'hf_13_%s.log' % pre)
    if os.path.exists(p):
        v = tl(p, 'ym2203', 0x40, 0x50)
        print('hf_13_%-4s YM2203 TL writes %3d  values %s' % (pre, len(v), ' '.join('%02x' % x for x in v)))
print()
for tag, chip in (('ho1_3f', 'oki1'), ('ho2_0e', 'oki2')):
    for pre in ('none', 'c8', 'cf', 'c0', 'c7'):
        p = os.path.join(HERE, 'out', '%s_%s.log' % (tag, pre))
        if os.path.exists(p):
            b = blk(p)
            w = A.decode(b['ev'])
            s, t = A.oki_events(w, chip)
            print('%s_%-4s %s starts %d  (phrase/voice/att) %s' % (tag, pre, chip, len(s), ' '.join('%d/%x/%d' % (x[1], x[2], x[3]) for x in s[:6])))
