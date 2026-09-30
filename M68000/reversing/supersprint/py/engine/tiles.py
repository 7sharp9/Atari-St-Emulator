"""Playfield tile pack (SUPER.DAT block at -1196(A4): file offset 52566, 80000 bytes) and the map renderer ($152d2).

Header (10 bytes, $14c4a): word0 = number of 40x25 tile maps (11), word1..word4 = tile counts of banks 0..3.
Maps:  count * 2000 bytes (1000 words: 25 rows x 40 columns of 8x8 tiles).
Banks: bank b (b=0..2) tiles are 8*(b+1) bytes of plane data (plane p = 8 rows of 1 byte at +8p) + 1 word 'colour mask'
       (10, 18, 26 bytes); bank 3 tiles are 32 raw bytes (4 planes x 8 rows).
Map word: bit15 = 1 -> tile: bit14 = flip-H, bit13 = flip-V, bits12..11 = bank, bits10..0 = tile index.
          bit15 = 0 -> the word is a byte offset into the screen being built: copy that 8x8 block (4 plane bytes x 8 rows)
          from the screen already drawn (screen-to-screen duplicate; 'dedupe' compression).
Bank 0..2 expansion (asm $15366-$1540e): the mask word is the tile's colour SET (bit c = colour c used). Walking c = 15..0,
the k-th set bit found (k = 0,1,2,...) is the colour of stored value k (v = p0 + 2*p1 + 4*p2): the value counter and the
plane-toggle state only advance when a set bit is consumed ($153b4 branches past the whole body, counter update included).
Pixels whose value has no colour stay colour 0.
"""
import struct

BANK_STRIDE = (10, 18, 26, 32)


class TilePack:
    def __init__(s, blk):
        s.blk = blk
        s.nmaps, n0, n1, n2, n3 = struct.unpack_from('>5H', blk, 0)
        s.counts = (n0, n1, n2, n3)
        s.maps_off = 10
        s.bank_off = []
        o = 10 + s.nmaps * 2000
        for b in range(4):
            s.bank_off.append(o)
            o += s.counts[b] * BANK_STRIDE[b]
        s.end = o

    def map_words(s, m):
        return struct.unpack_from('>1000H', s.blk, s.maps_off + m * 2000)

    def tile_planes(s, bank, idx):
        """-> list of 4 planes, each 8 row-bytes, exactly as the blitter would expand them (banks 0..2 use the mask word)."""
        o = s.bank_off[bank] + idx * BANK_STRIDE[bank]
        if bank == 3:
            return [list(s.blk[o + 8 * p:o + 8 * p + 8]) for p in range(4)]
        n = bank + 1
        raw = [list(s.blk[o + 8 * p:o + 8 * p + 8]) for p in range(n)]
        mask = struct.unpack_from('>H', s.blk, o + 8 * n)[0]
        cols = [c for c in range(15, -1, -1) if (mask >> c) & 1]     # colour of stored value k = cols[k]
        out = [[0] * 8 for _ in range(4)]
        for r in range(8):
            for bit in range(8):
                v = 0
                for p in range(n):
                    v |= ((raw[p][r] >> (7 - bit)) & 1) << p
                if v < len(cols):
                    c = cols[v]
                    for p in range(4):
                        if (c >> p) & 1:
                            out[p][r] |= 1 << (7 - bit)
        return out


def flip_h_byte(b):
    return int('{:08b}'.format(b)[::-1], 2)


def render_map(pack, m, screen=None):
    """Render map m into a 32000-byte ST screen (bytearray), following $152d2 exactly (incl. flips and screen-copy words)."""
    scr = bytearray(32000) if screen is None else screen
    words = pack.map_words(m)
    wi = 0
    for row in range(25):
        for col in range(40):
            w = words[wi]; wi += 1
            base = row * 1280 + (col >> 1) * 8 + (col & 1)      # byte address of plane-0 byte of row 0 of this tile
            if not (w & 0x8000):
                src = w
                for r in range(8):
                    for p in range(4):
                        scr[base + r * 160 + 2 * p] = scr[src + r * 160 + 2 * p]
                continue
            bank = (w >> 11) & 3; idx = w & 0x7ff
            planes = pack.tile_planes(bank, idx)
            fl = (w >> 13) & 3
            for r in range(8):
                rr = (7 - r) if (fl & 1) else r
                for p in range(4):
                    b = planes[p][rr]
                    if fl & 2:
                        b = flip_h_byte(b)
                    scr[base + r * 160 + 2 * p] = b
    return scr
