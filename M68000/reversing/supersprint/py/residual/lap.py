"""Python transcription of the lap-panel composer $158ea(dst, car).

$158ea draws, per car (0 blue, 1 red, 2 yellow), TWO 32x11-pixel strips of the HUD panel from a 6-byte digit state:
  state bytes b0..b5 are image indices (0..9, or >= $80 = blank). Strip A (right, dst+$470/+$4a8/+$4e0 for car 0/1/2) is built from
  set3[b5] (16 px, +1320, 44 B/img) | set1[b3] (+440, 44 B) | big set5[b4] (32 px ink+keep, +2640, 88 B); strip B (left, 16 bytes
  further left) from set2[b2] (+880) | set0[b0] (+0) | big set4[b1] (+1760).  An image is 11 rows x (ink word, keep word); the two
  16-px images are concatenated into one long (set1/set0 word in the high half, set3/set2 word in the low half) and OR/AND-ed with the
  big digit's ink/keep longs.  b2 < 0 (blank) trims strip A's set-1 image (ink &= $3fff, keep |= $c000), otherwise the trim is skipped.
  Each row's keep long goes to the depth layer, the composed 4 longs (over the pristine background) to the screen and the stash.
  On an EVEN frame parity (-8072(A4) & 1 == 0) the state -4846(A4)+6*car is first latched into -4870(A4)+6*car.
B7 = SUPER.DAT @165566 (3520 B).  blank images: 44 B at -4988(A4) (set images), 88 B at -5076(A4) (big image)."""
import struct

STRIPS = {  # car: [(dst offset, bg offset, layer offset, byte indices (A3 set, A2 big, A1 set), A3 off, A2 off, A1 off, trim?)]
    0: [(0x470, 0x10, 0x3F9C, (5, 4, 3), 1320, 2640, 440, True), (0x460, 0x00, 0x3F98, (2, 1, 0), 880, 1760, 0, False)],
    1: [(0x4A8, 0x48, 0x3FAA, (11, 10, 9), 1320, 2640, 440, True), (0x498, 0x38, 0x3FA6, (8, 7, 6), 880, 1760, 0, False)],
    2: [(0x4E0, 0x80, 0x3FB8, (17, 16, 15), 1320, 2640, 440, True), (0x4D0, 0x70, 0x3FB4, (14, 13, 12), 880, 1760, 0, False)],
}
M32 = 0xFFFFFFFF


def _img(b7, blank, idx, base, stride):
    return blank if idx & 0x80 else (b7, base + idx * stride)


def draw(dst, stash, layer, bgbuf, b7, blank44, blank88, state18, car):
    """dst/stash: bytearray screen images; layer: bytearray starting at -94(A4); bgbuf: bytes starting at the -4940(A4) pointer;
    state18: the 18-byte -4870(A4) array (already latched). Mutates dst/stash/layer."""
    for (do, bo, lo, (i3, i2, i1), o3, o2, o1, trim) in STRIPS[car]:
        s3, s2, s1 = state18[i3], state18[i2], state18[i1]
        # the trim flag is the sign of the byte just below the first index triple: b2 for car 0 (index 2), b8 for car 1, b14 for car 2
        flag = state18[i1 - 1] if trim else None
        a3 = blank44 if s3 & 0x80 else b7[o3 + s3 * 44:o3 + s3 * 44 + 44]
        a2 = blank88 if s2 & 0x80 else b7[o2 + s2 * 88:o2 + s2 * 88 + 88]
        a1 = blank44 if s1 & 0x80 else (b7[o1 + s1 * 44:o1 + s1 * 44 + 44])
        do_trim = trim and (flag & 0x80)
        for r in range(11):
            D3, D2 = struct.unpack_from('>HH', a1, r * 4)
            if do_trim:
                D3 &= 0x3FFF; D2 |= 0xC000
            D3 = (D3 << 16) | struct.unpack_from('>H', a3, r * 4)[0]
            D2 = (D2 << 16) | struct.unpack_from('>H', a3, r * 4 + 2)[0]
            ink, keep = struct.unpack_from('>II', a2, r * 8)
            D3 |= ink; D2 &= keep
            struct.pack_into('>I', layer, lo + r * 0x28, D2)
            H3, L3 = D3 >> 16, D3 & 0xFFFF
            D7 = ((D2 >> 16) << 16) | (D2 >> 16)
            D2n = ((D2 & 0xFFFF) << 16) | (D2 & 0xFFFF)
            bg = struct.unpack_from('>4I', bgbuf, bo + r * 160)
            if car == 0:
                out = [(bg[0] & D7) | (H3 << 16), bg[1] & D7, (bg[2] & D2n) | (L3 << 16), bg[3] & D2n]
            elif car == 1:
                out = [(bg[0] & D7) | H3, (bg[1] & D7) | H3, (bg[2] & D2n) | L3, (bg[3] & D2n) | L3]
            else:
                out = [bg[0] & D7, (bg[1] & D7) | (H3 << 16) | H3, bg[2] & D2n, (bg[3] & D2n) | (L3 << 16) | L3]
            o = do + r * 160
            for k in range(4):
                struct.pack_into('>I', dst, o + 4 * k, out[k] & M32)
                struct.pack_into('>I', stash, o + 4 * k, out[k] & M32)
