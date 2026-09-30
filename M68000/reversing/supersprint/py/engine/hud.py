"""HUD big digits: $15e5a(dst, car).  B7 (-4936(A4); SUPER.DAT @165566) set 5 at +$a50: 10 digits x 88 B = 11 rows x (ink long, keep-mask
long); each long = (word for px 0..15, word for px 16..31).  Panel cars 0/1/2 draw at fixed screen offsets (+$480/+$4b8/+$4f0 of the
draw screen and the stash) over the pristine panel background kept at -4940(A4); the ink goes into plane 0 (colour 1) for car 0,
planes 1+3 (colour 10) for car 1, planes 2+3 (colour 12) for car 2; the keep mask is also stored in the depth layer at
-94(A4)+$3e80 (+$120/+$12e/+$13c) so cars are hidden behind digits.  Transcription below works on byte images of those buffers."""
import struct

PATH = {0: dict(scr=0x480, bg=0x20, lay=0x120), 1: dict(scr=0x4B8, bg=0x58, lay=0x12E), 2: dict(scr=0x4F0, bg=0x90, lay=0x13C)}


def digit_rows(b7, digit):
    return [struct.unpack_from('>II', b7, 0xA50 + digit * 88 + r * 8) for r in range(11)]


def draw_digit(dst, stash, lay2, bgbuf, rows, car):
    """dst/stash: bytearrays (screen images) ; lay2: bytearray layer region starting at -94(A4)+$3e80 ; bgbuf: bytes of -4940(A4) region.
    Returns nothing; mutates dst/stash/lay2."""
    p = PATH[car]
    so = p['scr']; bo = p['bg']; lo = p['lay']
    for r, (ink, msk) in enumerate(rows):
        struct.pack_into('>I', lay2, lo + r * 0x28, msk)
        H, L = msk >> 16, msk & 0xFFFF
        D7 = (H << 16) | H; D2 = (L << 16) | L
        bg = struct.unpack_from('>4I', bgbuf, bo + r * 160)   # the background buffer has the screen's 160-byte row stride
        H3, L3 = ink >> 16, ink & 0xFFFF
        if car == 0:
            D3 = (H3 << 16); D4 = (L3 << 16)
            out = [(bg[0] & D7) | D3, bg[1] & D7, (bg[2] & D2) | D4, bg[3] & D2]
        elif car == 1:
            out = [(bg[0] & D7) & 0xFFFFFFFF, (bg[1] & D7), (bg[2] & D2), (bg[3] & D2)]
            out[0] |= H3; out[1] |= H3; out[2] |= L3; out[3] |= L3
        else:
            D3 = (H3 << 16) | H3; D4 = (L3 << 16) | L3
            out = [bg[0] & D7, (bg[1] & D7) | D3, bg[2] & D2, (bg[3] & D2) | D4]
        o = so + r * 160
        for k in range(4):
            struct.pack_into('>I', dst, o + 4 * k, out[k] & 0xFFFFFFFF)
            struct.pack_into('>I', stash, o + 4 * k, out[k] & 0xFFFFFFFF)
