"""The per-room terrain 'tile stack' unpacker ($00add0-$00ae8c) in Python, proved against the live 320-byte table.

Algorithm (transcribed from the code; graphics.md 5b/5e give the semantics):
  stream = the room's type-1 byte stream; W, H = room record bytes +4 and +5 (widths of the two passes).
  out = 320 zero bytes at (A5)+2914 = two 160-byte planes (width pass, height pass); a plane = 10 columns x 16 bytes,
  a column = 8 cells x 2 bytes ( [attribute byte][tile byte] ).
  D7 = stream[0]  (stack depth; 0 ends the room: table left all zero)
  group $00ae64: b = next byte; if b != 0:  v0 = b & 15, n0 = next byte  ->  n0 cells of plane 0 get attribute byte v0
       (the fill starts at byte offset 0 of plane 0 and steps 2 bytes, i.e. the EVEN bytes of the first n0 cells in
       row-major byte order, ignoring column boundaries); v1 = b >> 4, n1 = next byte -> same fill on plane 1 (+$a0).
       A nibble of 0 writes nothing for that plane (its count byte is still consumed).  b == 0: one byte, no fill.
  then for each of W columns: D7 tile bytes -> odd bytes of that column's first D7 cells (plane 0, column stride 16);
  then for each of H columns: D7 tile bytes -> plane 1.
Run from M68000/:  python3 reversing/cadaver/py/secrets/tile_stack_rle.py
Prints per room snapshot: the (W,H) for which the Python table equals the live table, and the byte match count (320/320).
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from ram import ram
A5 = 0x18152
def unpack(stream, W, H):
    out = bytearray(320); p = 0
    d7 = stream[p]; p += 1
    if d7 == 0: return bytes(out), p
    def fill(base, nib, cnt):
        if nib:
            for k in range(cnt): out[base + 2 * k] = nib
    b = stream[p]; p += 1
    if b:
        n0 = stream[p]; fill(0, b & 15, n0)
        p += 1; n1 = stream[p]; fill(0xa0, b >> 4, n1); p += 1
    for plane, n in ((0, W), (0xa0, H)):
        for col in range(n):
            for k in range(d7):
                out[plane + 16 * col + 2 * k + 1] = stream[p]; p += 1
    return bytes(out), p
if __name__ == '__main__':
    M68 = os.path.abspath(os.path.join(here, '..', '..', '..', '..'))
    for name, snap, addr, ln in (('CAVERN', 'gameplay_empire.snap', 0x4eb8a, 122), ('TUNNEL', 'room2_tunnel_entry.snap', 0x4ec04, 42)):
        r = ram(os.path.join(M68, 'scratchpad/cadaver', snap))
        live = r[A5 + 2914:A5 + 2914 + 320]; stream = r[addr:addr + ln]
        best = None
        for W in range(1, 11):
            for H in range(1, 11):
                try: out, used = unpack(stream, W, H)
                except IndexError: continue
                m = sum(a == b for a, b in zip(out, live))
                if best is None or m > best[0]: best = (m, W, H, used)
        print('%s: best W=%d H=%d -> %d/320 bytes match live table, stream bytes used %d of %d' % (name, best[1], best[2], best[0], best[3], ln))
