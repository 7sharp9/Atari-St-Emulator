#!/usr/bin/env python3
"""anims.py: resolve and walk the animations that kind 8's setters select (setter bodies $36e24.., table +12 words indexed by
the subtype byte 20(A6), animation = table + word) using the walker's format from $3b10/$3b3c [R]:
animation P: entries at P+4k {word off_k (frame data = P+4k+off_k), word delay/ctl}; delay high byte = frame count, a negative
word = loop: the entry's off is the (relative) jump back.  Frame data: +2..+5 -> record +42..+45 (+44 hurt box, +45 attack box),
+6 word -> +48.
usage: anims.py <setter-addr-hex> [sub]"""
import os, sys
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
sw = lambda a: (w(a) ^ 0x8000) - 0x8000
def walk(P, maxn=64):
    out = []; k = 0; q = P
    while k < maxn:
        off = sw(q); dly = w(q + 2)
        if dly & 0x8000:
            out.append(('LOOP', off, q, (q + off - P) // 4)); break
        fd = q + off
        out.append((q, dly >> 8, dly & 0xff, fd, rom[fd+2], rom[fd+3], rom[fd+4], rom[fd+5], w(fd+6), w(fd)))
        q += 4; k += 1
    return out
def setter_anim(addr, sub=0):
    # 36e24-style: move.b 20(A6),D0 / lea 6(PC),A1 / jmp $3b10
    tab = addr + 12
    return tab + sw(tab + 2 * sub), tab
if __name__ == '__main__':
    addr = int(sys.argv[1], 16); sub = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if w(addr) == 0x4a2e:  # 36f14: tst.b 99(A6) variant
        print('99(A6)!=0 -> fixed animation $400c'); addr = addr + 16
    P, tab = setter_anim(addr, sub)
    print('setter %x table %x anim %x' % (addr, tab, P))
    for r in walk(P):
        if r[0] == 'LOOP': print('  LOOP back to frame', r[3]); break
        q, cnt, flag, fd, b42, b43, b44, b45, w48, w0 = r
        print('  @%x cnt=%d ev=%02x fd=%x hurt=%02x atk=%02x b42=%02x b43=%02x w48=%04x sprite=%04x' % (q, cnt, flag, fd, b44, b45, b42, b43, w48, w0))
