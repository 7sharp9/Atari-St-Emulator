"""tile_usage.py: which tile-pack tiles (4 banks) are referenced by which of the 11 tile maps (tiles.py map-word format: bit15 = tile,
bits12..11 bank, bits10..0 index; bit15 = 0 words are screen-copy offsets).  Reports, per bank, the tiles no map references (never
indexed), and the SUPER.DAT file range of the highest-numbered referenced tile per map."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *
sys.path.insert(0, os.path.join(sscfg.R, 'reversing', 'supersprint', 'py', 'engine'))
from tiles import TilePack, BANK_STRIDE
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
P = TilePack(dat[0xcd56:0xcd56 + 80000])
used = [collections.defaultdict(set) for _ in range(4)]      # bank -> tile -> {maps}
for m in range(P.nmaps):
    for w in P.map_words(m):
        if w & 0x8000: used[(w >> 11) & 3][w & 0x7ff].add(m)
print('maps', P.nmaps, 'bank counts', P.counts)
for b in range(4):
    n = P.counts[b]; un = [i for i in range(n) if i not in used[b]]
    only_hi = [i for i in range(n) if i in used[b] and min(used[b][i]) >= 4]
    print('bank %d: %d tiles, %d referenced, %d never referenced %s; referenced only by maps >= 4: %d' % (b, n, n - len(un), len(un), un[:40], len(only_hi)))
    if b == 2 and only_hi:
        lo, hi = min(only_hi), max(only_hi)
        print('   bank2 tiles first used by maps >= 4: index %d..%d = file %x..%x' % (lo, hi, 0xcd56 + P.bank_off[2] + lo * 26, 0xcd56 + P.bank_off[2] + (hi + 1) * 26))
# per map: tile counts
for m in range(P.nmaps):
    ws = P.map_words(m); t = sum(1 for w in ws if w & 0x8000)
    print('map %d: tile words %d, copy words %d' % (m, t, len(ws) - t))
