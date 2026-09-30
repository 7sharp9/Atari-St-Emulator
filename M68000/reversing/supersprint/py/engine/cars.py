"""Car sprite sheet (SUPER.DAT block at -3602(A4): file offset 19798, 32768 bytes = 128 frames x 256 bytes) and the car blitter ($14a4a).

Frame index f = 16*car + heading (+64 when -3914(A4)[car] != 0); frame f is at block + f*256.
A frame is 12 rows x 16 bytes (rows 12..15 of the 256-byte slot are unused/junk). A row = 4 longs L0..L3 (stored planes); each long
holds the 16-pixel plane word in its HIGH half; screen words written are [L0, L2, L1, L3] after a ror by (x&15) across a 32-bit window.
Transparent pixel = stored planes L0=L1=L2=0 and L3=1 (screen colour 8).
"""
import struct
from sprites import ror32, M32


def frame_rows(blk, f):
    return [struct.unpack_from('>4I', blk, f * 256 + r * 16) for r in range(12)]


def frame_pixels(blk, f):
    """-> 12x16 list of colour indices (screen colour, i.e. with the [0,2,1,3] plane permutation), None where transparent."""
    out = []
    for row in frame_rows(blk, f):
        w = [(v >> 16) for v in row]
        line = []
        for b in range(16):
            sh = 15 - b
            l0, l1, l2, l3 = [(w[i] >> sh) & 1 for i in range(4)]
            if l0 == 0 and l1 == 0 and l2 == 0 and l3 == 1:
                line.append(None)
            else:
                line.append(l0 | (l2 << 1) | (l1 << 2) | (l3 << 3))
        out.append(line)
    return out


def car_blit(scr, blk, f, x, y, layer0=None, layer2=None, flag=0):
    """Transcription of $14a4a. scr: bytearray screen. layer0/layer2: callables (byte_offset_in_mono_bitmap) -> 32-bit long
    (the 1bpp priority bitmaps at -94(A4)+0 and +16000; the +8000 one is only saved). flag = the byte at $14b88."""
    s = x & 15
    d0 = ((x & 0xFFF0) >> 1) + y * 160
    rows = frame_rows(blk, f)
    for r, (l0, l1, l2, l3) in enumerate(rows):
        D3, D4, D5, D6 = [ror32(v, s) for v in (l0, l1, l2, l3)]
        D2 = (~D6 & M32) | D3 | D4 | D5
        if not (flag & 0x80):
            mo = ((d0 + r * 160) >> 2)
            if layer0 is not None:
                D6 &= layer0(mo)
            if flag == 0 and layer2 is not None:
                D2 &= layer2(mo)
        D3 &= D2; D4 &= D2; D5 &= D2; D6 &= D2
        K = ~D2 & M32
        Kh, Kl = K >> 16, K & 0xFFFF
        vals = ((D3 >> 16, D5 >> 16, D4 >> 16, D6 >> 16), (D3 & 0xFFFF, D5 & 0xFFFF, D4 & 0xFFFF, D6 & 0xFFFF))
        base = d0 + r * 160
        for g, (v, k) in enumerate(zip(vals, (Kh, Kl))):
            for p in range(4):
                o = base + g * 8 + 2 * p
                if 0 <= o < len(scr) - 1:
                    cur = (scr[o] << 8) | scr[o + 1]
                    cur = (cur & k) | v[p]
                    scr[o] = cur >> 8; scr[o + 1] = cur & 255
