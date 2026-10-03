"""e4_l1_lever562.py: level 1 object 562 (room 90, template 104: lever animation `00 00 f9 00 00 01 f9 00 fd 00`) answering its own event-5 script
(3 GOANI actor, 55 UNLOCK #670, 11 GOMOVE #670, 0 DELETE #213, 0 DELETE #214): event 5 injected into the ring (the consumer runs the block), then per-pass traces of
562's anim block / +15 and 670's +3, +15, mover block and position, each pass compared with anim_model / mover_model.
Start: scratchpad/cadaver/s90/run1/end_room90.snap (room 90, objects 0, 562, 670; 213 and 214 live in another room).   usage: e4_l1_lever562.py"""
import sys
from lab import *
import anim_model, mover_model
from st import St
SNAP = SN('ROOM90', 'scratchpad/cadaver/s90/run1/end_room90.snap')
s = St(SNAP)
tm562 = bytes(s.mem(s.tmpl((s.b(s.obj(562) + 6) << 8) | s.b(s.obj(562) + 7)), 0x100))
r = start(SNAP); passes(r, 2)
def snapst():
    a = rec_of(r, 562); b = rec_of(r, 670)
    ha = r.mem(a, 16); hb = r.mem(b, 16)
    return dict(anim=bytearray(r.mem(a + ha[14], 10)), f15a=ha[15], f3b=hb[3], f15b=hb[15], mv=bytearray(r.mem(b + hb[13], hb[14] - hb[13])), pos=bytes(r.mem(b, 3)),
                n213=rec_of(r, 213) is not None, n214=rec_of(r, 214) is not None)
print('before: ', {k: (v.hex(' ') if isinstance(v, (bytes, bytearray)) else v) for k, v in snapst().items()})
fire(r, 562, 5)
rows = []
for k in range(40):
    rows.append(snapst()); passes(r, 1)
mk = lambda v: v.hex(' ') if isinstance(v, (bytes, bytearray)) else v
ok_a = n_a = ok_m = n_m = 0
print('pass  562 anim block / +15        670 +3 +15  mover block (state cursor counters)  pos')
for k, x in enumerate(rows[:34]):
    note = ''
    if k + 1 < len(rows):
        y = rows[k + 1]
        # anim model on 562 (GOANI happens during the consumer, after the pass; the model covers the pass itself)
        pa = bytearray(x['anim']); pf = x['f15a']
        if not pf & 1:
            ev, st = anim_model.step(tm562, pa); pf |= 1 if st else 0
        if y['f15a'] & 1 == 0 and pa[0] == 0xfe and pf & 1: pa[0] = 0; pa[3] += 1; pf &= ~1       # GOANI between passes
        good_a = bytes(pa[0:4]) == bytes(y['anim'][0:4]) and (pf & 1) == (y['f15a'] & 1); n_a += 1; ok_a += good_a
        pm = bytearray(x['mv']); d, ev, ended = mover_model.step(pm)
        mo = tuple((y['pos'][i] - x['pos'][i]) & 0xff for i in range(3))
        good_m = (bytes(pm) == bytes(y['mv']) and (d is None or tuple(v & 0xff for v in d) == mo)) or (x['mv'][0] == 1 and bytes(y['mv']) != bytes(x['mv']))  # state 1 -> GOMOVE between passes
        n_m += 1; ok_m += good_m
        note = ('A:%s M:%s' % ('ok' if good_a else 'X', 'ok' if good_m else 'X'))
    print('%3d  %s %02x    %02x  %02x   %s   %s   %s  213:%d 214:%d' % (k, mk(x['anim']), x['f15a'], x['f3b'], x['f15b'], mk(x['mv'][:6]), mk(x['pos']), note, x['n213'], x['n214']))
print('anim transitions matching anim_model: %d of %d; mover transitions matching mover_model: %d of %d' % (ok_a, n_a, ok_m, n_m))
r.close()
