"""Transcriptions of the game's sprite blitters, on a 320x200 ST-interleaved 4-plane screen (bytearray, 160 bytes/row).

Stored-plane order (proved from the swap sequences at $14b0a-$14b76, $14bf6-$14c3c, $15694-$156d2): a sprite row is four
planes w0..w3 and the blitter writes screen words [w0, w2, w1, w3] (screen plane 1 comes from stored plane 2 and vice versa).
"""
import struct

M32 = 0xFFFFFFFF


def rol32(v, n):
    n &= 31
    return ((v << n) | (v >> (32 - n))) & M32 if n else v & M32


def ror32(v, n):
    return rol32(v, (32 - (n & 31)) & 31)


def put_group(scr, base, kh_kl, vh, vl):
    """base = byte offset of screen group 0; vh/vl = 4-word tuples in screen order for group 0 / 1;
    kh_kl = (keep mask for group0, keep mask for group1), each a 16-bit word applied to all four planes."""
    for g, (v, k) in enumerate(((vh, kh_kl[0]), (vl, kh_kl[1]))):
        for p in range(4):
            o = base + g * 8 + 2 * p
            if 0 <= o < len(scr) - 1:
                cur = (scr[o] << 8) | scr[o + 1]
                cur = (cur & k) | v[p]
                scr[o] = cur >> 8; scr[o + 1] = cur & 255


def blit_masked_rows(scr, x, y, rows, rotate):
    """rows: list of (w0,w1,w2,w3) stored-order 16-bit planes. rotate='ror' -> car sprite ($14a4a: source long has the word in
    the HIGH half, ror by x&15) or 'rol' -> ($15642/$14b8e: word in the LOW half, rol by 16-(x&15)).
    transparent where ALL of w0|w1|w2|w3... see callers for the exact mask rule (passed via `mask_fn`)."""
    raise NotImplementedError


def tree_sprite(scr, x, y, rows16):
    """$15642 part 1. rows16 = 16 rows of (w0,w1,w2,w3). Opaque wherever any plane bit is set (colour 0 transparent)."""
    n = ((~x) & 15) + 1
    base0 = ((x & 0xFFF0) >> 1) + y * 160
    for r, w in enumerate(rows16):
        V = [rol32(w[i], n) for i in range(4)]
        K = ~(V[0] | V[1] | V[2] | V[3]) & M32
        Kh, Kl = K >> 16, K & 0xFFFF
        vh = (V[0] >> 16, V[2] >> 16, V[1] >> 16, V[3] >> 16)
        vl = (V[0] & 0xFFFF, V[2] & 0xFFFF, V[1] & 0xFFFF, V[3] & 0xFFFF)
        put_group(scr, base0 + r * 160, (Kh, Kl), vh, vl)


def shadow_words(w, m):
    """$15774-$15794 on one 16-px group: w = 4 screen plane words (p0..p3), m = shadow mask word.
    colour 13 -> 5 and colour 8 -> 3 inside the mask (grass and tarmac darken)."""
    d0, d1, d2, d3 = w
    d5 = (~d1 & d0 & d2 & d3 & m) & 0xFFFF
    d5 = ~d5 & 0xFFFF
    d3 &= d5
    nm = ~m & 0xFFFF
    d5 = (~d3 & 0xFFFF) | d0 | d1 | d2 | nm
    d5 &= 0xFFFF
    d3 &= d5
    d5 = ~d5 & 0xFFFF
    d0 |= d5; d1 |= d5
    return d0, d1, d2, d3


def tree_shadow(scr, x, y, typ, shadow_rows, dyl):
    """$15642 part 2. shadow_rows = list of 16-bit words (row data for this type), dyl = (dy, len) from the table at $157da.
    x' = x-8 (types 0..2; type 3 keeps x).  If x-8 < 0 the routine sets x'=8 and a marker that skips the FIRST group's
    darkening; A1 is then not advanced, so the second-group pass (mask = the low half of the rotated word) is applied to the
    screen group at byte offset 0, i.e. the shadow's right 8 pixels land on x=0..7."""
    xx = x
    clamp = False
    if typ != 3:
        xx -= 8
        if xx < 0:
            clamp = True; xx = 8
    n = ((~xx) & 15) + 1
    d0 = (xx & 0xFFF0) >> 1
    y0 = y + dyl[0]
    yend = min(y0 + dyl[1], 200)
    for k, row in enumerate(range(y0, yend)):
        D6 = rol32(shadow_rows[k], n)
        H, L = D6 >> 16, D6 & 0xFFFF
        o = d0 + row * 160
        if not clamp:
            _apply(scr, o, H)
            _apply(scr, o + 8, L)
        else:
            _apply(scr, o, L)


def _apply(scr, o, m):
    if not (0 <= o < len(scr) - 7):
        return
    w = [(scr[o + 2 * p] << 8) | scr[o + 2 * p + 1] for p in range(4)]
    w = shadow_words(w, m)
    for p in range(4):
        scr[o + 2 * p] = w[p] >> 8; scr[o + 2 * p + 1] = w[p] & 255


def sext16(w):
    return (w | 0xFFFF0000) if (w & 0x8000) else w


def spinout_sprite(scr, x, y, rows14):
    """$14b8e (car EXPLOSION debris frame, 26 frames of 16x14): drawn like a tree sprite EXCEPT the source words are loaded with movem.w (sign-extended to 32 bits, so a
    set bit 15 rotates ones into the low bits) and only stored plane 3 is masked (D6 &= opaque); planes 0..2 are OR-ed unmasked."""
    n = ((~x) & 15) + 1
    base0 = ((x & 0xFFF0) >> 1) + y * 160
    for r, w in enumerate(rows14):
        V = [rol32(sext16(w[i]), n) for i in range(4)]
        D2 = (~V[3] & M32) | V[0] | V[1] | V[2]
        V[3] &= D2
        K = ~D2 & M32
        vh = (V[0] >> 16, V[2] >> 16, V[1] >> 16, V[3] >> 16)
        vl = (V[0] & 0xFFFF, V[2] & 0xFFFF, V[1] & 0xFFFF, V[3] & 0xFFFF)
        put_group(scr, base0 + r * 160, (K >> 16, K & 0xFFFF), vh, vl)


def wrench_sprite(scr, x, y, rows16):
    """$1404e (TORNADO, 3 frames of 16x16): like tree_sprite but clipped vertically: y<0 skips |y| source rows, y>=$b9 loses (y-$b8) rows."""
    n_rows = 15
    src0 = 0
    if y < 0:
        k = -y; n_rows -= k; src0 = k; y = 0
    elif y >= 0xB9:
        n_rows -= (y - 0xB8)
    rows = rows16[src0:src0 + n_rows + 1]
    tree_sprite(scr, x, y, rows)


def blit_rows_masked_groups(scr, x_group_bytes, y, rows, ngroups):
    """$13cbc/$13d58 style: rows = list of (list of ngroups x 4 words [p0,p1,p2,p3] screen order, list of ngroups keep-mask words); byte-aligned
    (16-px group) placement: out = (screen & keep) | ink per plane word."""
    for r, (inks, keeps) in enumerate(rows):
        for g in range(ngroups):
            for p in range(4):
                o = x_group_bytes + (y + r) * 160 + g * 8 + 2 * p
                if 0 <= o < len(scr) - 1:
                    cur = (scr[o] << 8) | scr[o + 1]
                    cur = (cur & keeps[g]) | inks[g][p]
                    scr[o] = cur >> 8; scr[o + 1] = cur & 255
