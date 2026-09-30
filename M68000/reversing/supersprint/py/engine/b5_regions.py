"""SUPER.DAT block B5 (-1722(A4), file offset 132566, 30000 B) region map, from the blitters that read it:
  $0000..$017f  3 x 128 B   TORNADO frames (grey whirlwind), 16x16, stored [w0..w3] per row, screen words [w0,w2,w1,w3], colour 0 transparent ($1404e)
  $0180..$0cbf  5 x 576 B   48x16 'dressing' objects with depth-layer masks ($142b2): per row 3 screen groups (24 B) + 12 B layer words
  $0cc0..$123f  22 x 64 B   16x8 opaque screen-format images: score pop-ups 1/10/100/1000/15/150/2/20/200/25/250, 3 oil/water slicks, WRENCH (#19), cone (#21) ($14262)
  $1240..$173f  44 x 32 B   8x8 smoke-puff frames, rows of 4 plane bytes [p0 p1 p2 p3], colour 8 (only plane 3) transparent ($143ca)
  $1740..$1bbf  12 x 96 B   16x8 grey posts/bollards, colour 0 transparent, plus two layer words per row ($1432e)
  $1bc0..$24bf  36 x 64 B   16x8 track-dressing sprites (chevrons, flags, leaves), rows of 4 words (movem.w, sign-extended), plane-3-only pixels transparent ($1416c)
  $24c0..$3b3f   8 x 720 B  HELICOPTER small 32x36 (20 B per row: 2 groups x 4 planes + keep-mask long; $13cbc, loaded by $13f88)
  $3b40..$5bbf   8 x 1040 B HELICOPTER large 64x26 (2 x 20 B per row; $13d58 with clipping)
  $5bc0..$671f  26 x 112 B  car EXPLOSION frames 16x14 (proved, $14b8e)
  $6720..$6eff   6 x 336 B  16x? (6 rows of 7 longs: $144ca, car-variant pairs)            [format from code, see below]
  $6f00..$70df  10 x 48 B   $1453a: 6 rows x (2 longs)  (per-car turbo/upgrade icon?)       [format from code]
  $70e0..$72df   4 x 128 B  tree/scenery sprites 16x16 (proved, $15642)
  $72e0..$735f   4 x 32 B   tree shadow masks, 16 words (proved)
"""
import struct
from sprites import rol32, M32


def planes_to_pixels(words, permuted=True, transparent=None):
    """words = 4 x 16-bit row words (stored order). permuted: screen plane1<-stored2, plane2<-stored1 (car/tree order)."""
    w0, w1, w2, w3 = words
    if permuted:
        p = [w0, w2, w1, w3]
    else:
        p = [w0, w1, w2, w3]
    row = []
    for b in range(16):
        sh = 15 - b
        row.append(sum(((p[i] >> sh) & 1) << i for i in range(4)))
    return row


def sprite_words(blk, off, rows, stride_words=4):
    return [struct.unpack_from('>%dH' % stride_words, blk, off + r * stride_words * 2) for r in range(rows)]
