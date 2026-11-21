"""Frame-level check of the whole 3D viewport: for natural entries of the frame routine $fb74 (g_game1 / g_game2), the reference reproduces the
viewport (rows 10..128, bytes 8..151 of each 160-byte row = x 16..303, all four planes) of the buffer 0(A6) after the call:
    clear ($1455c: zero the viewport)  ->  ground dust ($f336, with the view matrix the call computed)  ->  every object on the final visible list
    148(A6) (574(A6) entries: $f6a8, or nothing for the type-0 / 36(A4)-flagged records) with its camera-space centre 40/42/44(A4).
The lists, the camera-space centres and the view matrix are read from the RAM AFTER the call (they are built by $ede4/$101a8/$10344, not modelled);
everything drawn is modelled.  The gunsight sprite ($10124 -> $143ce, at 580/582(A6)) is NOT modelled: its box is excluded from the count.
    python3 gate_frame.py <snap> [hit numbers ...]       Output: per frame `bytes matched / bytes compared`, unmatched byte list bounding box.
"""
import os, sys, json
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import rcommon as R
import rref as F
A6 = F.A6
snap = sys.argv[1] if len(sys.argv) > 1 else R.SNAP_GAME2
hits = [int(x) for x in sys.argv[2:] if x.isdigit()] or [1, 6, 11, 16]
OUT = R.WORK + '/render/caps/frame'
R.cap_calls(snap, 0xfb74, hits, OUT, 'f', callcap_steps=4000000)
tot_ok = tot = 0
for h in hits:
    j = json.load(open(f'{OUT}/f_{h}.json'))
    pre = bytearray(R.load_ram(f'{OUT}/f_{h}.snap')); post = bytearray(pre)
    for a, o, n in j['mem']: post[a] = n
    scr = int.from_bytes(pre[A6:A6 + 4], 'big')
    # 1. clear
    work = bytearray(pre)
    for y in range(10, 129):
        for b in range(8, 152): work[scr + 160 * y + b] = 0
    # 2. dust with the final view matrix (positions/camera from the pre state)
    d = bytearray(work)
    for o in list(range(360, 378)) + list(range(458, 470)): d[A6 + o:A6 + o + 2] = post[A6 + o:A6 + o + 2]
    m = F.Mem(d)
    if '--control' not in sys.argv: F.dust(m, j['reg0'][0])      # --control: the dust pass is left out
    for a, v in m.changes().items():
        if scr <= a < scr + 32000: work[a] = v
    # 3. objects on the final list, state from the post-call RAM
    base = bytearray(post); base[scr:scr + 32000] = work[scr:scr + 32000]
    m = F.Mem(base)
    lst = m.u32(A6 + 148); cnt = m.g(574)
    nobj = 0
    for i in range(cnt):
        rec = m.u32(lst + 4 * i)
        if m.u16(rec) == 0: continue
        m.sg(404, m.s16(rec + 40)); m.sg(406, m.s16(rec + 42)); m.sg(408, m.s16(rec + 44))
        m.sg(378, s := F.s16(m.s16(rec + 10) + m.g(314))); m.sg(380, F.s16(m.s16(rec + 12) + m.g(316))); m.sg(382, F.s16(-m.g(318)))
        if m.b(rec + 36) == 0:
            F.f6a8(m, m.u16(rec)); nobj += 1
    final = bytearray(base)
    for a, v in m.changes().items(): final[a] = v
    rx, ry = F.s16(int.from_bytes(post[A6 + 580:A6 + 582], 'big')), F.s16(int.from_bytes(post[A6 + 582:A6 + 584], 'big'))
    bx0 = (((rx - 14) >> 4) << 3); box = (bx0 - 8, bx0 + 32, ry - 8, ry + 9)     # the gunsight sprite $143ce blits 16 rows from (rx-14, ry-8), up to 3 word groups
    ok = n = 0; bad = []; nz = nzok = 0
    for y in range(10, 129):
        for b in range(8, 152):
            a = scr + 160 * y + b
            if box[0] <= b < box[1] and box[2] <= y < box[3]: continue          # excluded: the gunsight (not modelled)
            n += 1
            if post[a] or final[a]: nz += 1
            if final[a] == post[a]:
                ok += 1; nzok += bool(post[a] or final[a])
            else: bad.append((y, b))
    tot_ok += ok; tot += n
    bb = (min(b for y, b in bad), max(b for y, b in bad), min(y for y, b in bad), max(y for y, b in bad)) if bad else None
    pix_pre = sum(1 for y in range(10, 129) for b in range(8, 152) if pre[scr + 160 * y + b])
    pix_post = sum(1 for y in range(10, 129) for b in range(8, 152) if post[scr + 160 * y + b])
    print(f'hit {h}: objects drawn {nobj} of {cnt}; viewport bytes {ok}/{n} equal ({100*ok/n:.3f}%); nonzero bytes: before {pix_pre}, after {pix_post}; unmatched {len(bad)} bytes, box (x-byte {bb and bb[:2]}, y {bb and bb[2:]}); bytes drawn in either: {nz}, equal: {nzok}; gunsight box {box} excluded')
print(f'total {tot_ok}/{tot} = {100*tot_ok/tot:.3f}% of the viewport bytes outside the gunsight box')
os.system(f'rm -f {OUT}/f_*.snap')
