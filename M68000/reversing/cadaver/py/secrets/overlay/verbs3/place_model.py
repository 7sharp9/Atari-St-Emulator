"""place_model.py: a Python transcription of the free-space search $008e38 ($008e60-$008fec) used by verbs 36/41/44/73/84 and teleport, for comparison with live traces.
Input: base position (x, y, z), template extents w16, w18, w20, the world bounds (xmax, ymax, xmin_lo, ymin_lo = 2238, 2239, 2204, 2203 (A5)), the collision entries
[(x_hi, y_hi, x_lo, y_lo, z_hi, z_lo)] (all inclusive, signed byte compares), the direction mask D6 (verb 41 passes 63, verbs 36/44/84 use the slot masks).
Output: (cands, found): cands = [(x, y, z, D6 low byte at the call, D3, D4, D5)] in test order; found = (x, y, z) or None (D6 = 0: the callers' assert)."""

def s8(v):
    v &= 255
    return v - 256 if v & 128 else v

ENTRIES = [  # (mask, dx sign, dy sign, kind): the table at $008dee (first pass only: as-is $0f, fail $40) and $008dfa (every round)
    (0x01, 0, -1, 'xy'), (0x09, +1, -1, 'xy'), (0x08, +1, 0, 'xy'), (0x0a, +1, +1, 'xy'), (0x02, 0, +1, 'xy'), (0x06, -1, +1, 'xy'), (0x04, -1, 0, 'xy'), (0x05, -1, -1, 'xy'),
    (0x20, 0, 0, 'zm'), (0x10, 0, 0, 'zp')]

def overlap(c, e):
    D0, D1, D2, D3, D4, D5 = c
    xh, yh, xl, yl, zh, zl = [s8(v) for v in e]
    D0s, D1s, D3s, D4s = s8(D0), s8(D1), s8(D3), s8(D4)
    # x
    if D0s >= xh:
        if D3s > xh: return False
    else:
        if D0s < xl: return False
    # y
    if D1s >= yh:
        if D4s > yh: return False
    else:
        if D1s < yl: return False
    # z (words in D2/D5, byte compares)
    D2b, D5b = s8(D2), s8(D5)
    if D5b >= zh:
        return D2b <= zh
    return D5b >= zl

def model(x, y, z, w16, w18, w20, blockers, world=(80, 80, 6, 6), D6=63, maxcand=2000):
    xmax, ymax, xlo, ylo = world
    D0b, D1b, D2 = x, y, z
    D3b, D4b, D5 = x - w16 + 1, y - w18 + 1, z + w20 - 1
    step = 4; bit31 = False
    cands = []
    rnd = 0
    def test(dx, dy, kind):
        nonlocal D2, D5, D6, bit31
        D0, D1, D3, D4 = D0b + dx * step, D1b + dy * step, D3b + dx * step, D4b + dy * step
        if kind == 'zm': bit31 = True; D2 -= 1; D5 -= 1
        elif kind == 'zp': bit31 = True; D2 += 1; D5 += 1
        cands.append((D0 & 255, D1 & 255, D2 & 0xffff, D6 & 255, D3 & 0xffff, D4 & 0xffff, D5 & 0xffff))
        abort = False
        if (D2 & 0xffff) >= 0x8000:                      # tst.w D2; bpl
            if bit31: bit31 = False; D2 += 1; D5 += 1
            D6 &= ~0x20; abort = True
        if (D5 & 0xffff) >= 0xf0:                        # cmpi.w #$f0,D5; bcs
            if bit31: bit31 = False; D2 -= 1; D5 -= 1
            D6 &= ~0x10; abort = True
        if s8(D0) >= s8(xmax): D6 &= ~0x08; abort = True      # cmp.b 2238(A5),D0; blt
        if s8(D1) >= s8(ymax): D6 &= ~0x02; abort = True
        if s8(D3) < s8(xlo): D6 &= ~0x04; abort = True
        if s8(D4) < s8(ylo): D6 &= ~0x01; abort = True
        if abort: return False
        for e in blockers:
            if not overlap((D0, D1, D2, D3, D4, D5), e): continue
            return False
        return (D0 & 255, D1 & 255, D2 & 0xffff)
    first = True
    while len(cands) < maxcand:
        if first:
            if (D6 & 0x0f) == 0x0f:
                r = test(0, 0, 'xy')
                if r: return cands, r
                if (D6 & 255) == 0: return cands, None
            if (D6 & 0x40) == 0x40: return cands, None      # entry $40 -> $008eae: give up
        for (m, sx, sy, kind) in ENTRIES:
            if (D6 & m) == m:
                r = test(sx, sy, kind)
                if r: return cands, r
                if (D6 & 255) == 0: return cands, None
        first = False
        step += 4                                           # the table terminator: $008e8c adds 4 to both step words
    return cands, 'runaway'
