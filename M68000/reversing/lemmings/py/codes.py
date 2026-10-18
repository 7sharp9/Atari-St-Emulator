"""Lemmings (ST, Psygnosis 1990) access codes, from the game's own routines:
generator $3d40 (writes the 10 letters to $d802), checker $404c.
KEY is the 10 bytes at $27522."""
KEY = b"AJHLDHBBCJ"

def gen(n, f=0, p=0):
    """n = level index (50(A5), +$a0 for two-player), f = low nibble of 27(A5), p = percent rescued (54(A5))."""
    n &= 0xff; f &= 0xf; p &= 0xffff
    c = [0]*10
    c[0] = KEY[0] | ((n & 1) << 3) | ((f & 1) << 1) | ((p & 1) << 2)
    c[1] = KEY[1] | ((n & 2) << 1) | ((p & 2) >> 1)
    c[2] = KEY[2] | (n & 4) | ((f & 2) >> 1) | ((p & 4) >> 1)
    c[3] = KEY[3] | ((n & 8) >> 3) | ((p & 8) >> 2)
    c[4] = KEY[4] | ((n & 0x10) >> 3) | ((f & 4) >> 2) | ((p & 0x10) >> 1)
    c[5] = KEY[5] | ((n & 0x20) >> 5) | ((f & 8) >> 2) | ((p & 0x20) >> 3)
    c[6] = KEY[6] | ((n & 0xc0) >> 4) | ((p & 0x40) >> 6)
    c[7] = (KEY[7] + (n & 0xf)) & 0xff
    c[8] = (KEY[8] + ((n & 0xf0) >> 4)) & 0xff
    c[9] = (KEY[9] + (sum(c[:9]) & 0xf)) & 0xff
    for _ in range(8 - (n & 7)):          # rotate letters 0..6 right by one, 8-(n&7) times
        c[0:7] = [c[6]] + c[0:6]
    return bytes(c).decode("latin1")

def check(code):
    """Mirror of $404c. Returns (n, f) or None."""
    c = list(code.encode("latin1"))
    if len(c) != 10: return None
    if (c[9] - (sum(c[:9]) & 0xf)) & 0xff != KEY[9]: return None
    n = ((c[7] - KEY[7]) & 0xf) + 16 * ((c[8] - KEY[8]) & 0xf)
    for _ in range(8 - (n & 7)):          # rotate letters 0..6 left
        c[0:7] = c[1:7] + [c[0]]
    d = ((c[0] >> 3) & 1) | ((c[1] >> 1) & 2) | (c[2] & 4) | ((c[3] << 3) & 8) \
        | ((c[4] << 3) & 0x10) | ((c[5] << 5) & 0x20) | ((c[6] << 4) & 0xc0)
    if d != n: return None
    f = ((c[0] >> 1) & 1) | ((c[2] << 1) & 2) | ((c[4] << 2) & 4) | ((c[5] << 2) & 8)
    return n, f

if __name__ == "__main__":
    print(gen(0), gen(5), check(gen(5, 3, 77)))
