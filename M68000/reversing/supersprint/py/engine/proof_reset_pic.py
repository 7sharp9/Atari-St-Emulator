"""Proof: the reset-vector routine $10236 RLE-decodes the 8000-byte block at -126(A4) (SUPER.DAT offset 190966)
into the screen at -82(A4).  Python decoder (rle.py) vs the live routine (callcap delta): byte match count.
Also renders the credits/publisher picture with the reset palette (-5460(A4))."""
import sys, os, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from repl import Repl
import rle

snap = sscfg.SNAP_RACE
ram = Ram(snap)
blk = ram.g(-126); scr = ram.g(-82)
print('block -126(A4)=$%x  screen -82(A4)=$%x' % (blk, scr))
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
assert bytes(ram.b[blk:blk + 8000]) == dat[190966:190966 + 8000], 'block is not SUPER.DAT+190966'
print('block == SUPER.DAT[190966:+8000]: True')
out, used = rle.unrle_plane_major(rle.to_words(bytes(ram.b[blk:blk + 8000])))
mine = struct.pack('>%dH' % len(out), *out)
print('python decode consumed %d of 4000 words' % used)

tmp = os.path.join(OUT, 'callcap_reset.json')
r = Repl(snap)
o, _ = r.cmd('callcap 10236 30000000 %s' % tmp)
print('\n'.join(l for l in o if 'callcap' in l or 'regdelta' in l))
r.close()
delta = json.load(open(tmp))
live = bytearray(ram.b[scr:scr + 32000])
for ad, x0, x1 in delta['mem']:
    if scr <= ad < scr + 32000:
        live[ad - scr] = x1
same = sum(1 for a, b in zip(live, mine) if a == b)
print('screen bytes equal (python decode vs live callcap): %d / 32000' % same)
pal = palette_at(ram, A4 - 5460)
decode_st_screen(bytes(live), pal).save(os.path.join(PNG, 'reset_credits_picture.png'))
