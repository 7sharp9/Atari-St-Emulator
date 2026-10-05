# decode animations of kind-0 characters: thunk (lea 6(PC),A1 / jmp $3b10) tables -> frames, hurt/attack box indices, attack box records.
import sys, os
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def w(a): return int.from_bytes(rom[a:a+2], 'big')
def sw(a):
    v = w(a); return v - 65536 if v >= 32768 else v
def b(a): return rom[a]
def sb(a):
    v = rom[a]; return v - 256 if v >= 128 else v
CHARS = {0: ('BRED', 0x23e7c, 0x23f2c), 1: ('DUG', 0x24e1a, 0x24eca), 2: ('JAKE', 0x25dc0, 0x25e70), 3: ('CHAR3', 0x26d66, 0x26e16)}
# thunk start -> (table address = address of the 4 words)
THUNKS = {0x22dd4: 0x22de2, 0x22e00: 0x22e12, 0x22e1a: 0x22e2e, 0x22e36: 0x22e44, 0x22e4c: 0x22e5a, 0x22e62: 0x22e70,
          0x22e78: 0x22e86, 0x22e8e: 0x22e9c, 0x22ea4: 0x22eb2, 0x22eba: 0x22ec8, 0x22ed0: 0x22ede, 0x22ee6: 0x22ef4,
          0x22efc: 0x22f0a, 0x22f12: 0x22f20, 0x22f28: 0x22f36, 0x22f3e: 0x22f4c, 0x22f54: 0x22f62}
def anim(hdr):
    # header at hdr: list of (frame offset word, timer word) entries; frame record = entry_addr + off  (see $3b10/$3b3c)
    out = []
    a = hdr
    for _ in range(64):
        off = sw(a); tm = w(a + 2)
        if tm & 0x8000:           # loop marker: offset back to entry
            out.append(('loop', a + off)); break
        rec = a + off
        out.append(('frame', rec, tm >> 8, tm & 0xff))
        a += 4
    return out
def framerec(rec):
    return dict(rec=rec, w0=w(rec), b2=b(rec+2), b3=b(rec+3), hurt=b(rec+4), atk=b(rec+5), w6=w(rec+6))
def attackbox(ch, idx):
    base = CHARS[ch][1]
    p = base + (idx & 0x7f) * 16 + w(base)
    return dict(addr=p, dx=sw(p), dy=sw(p+2), hw=w(p+4), hh=w(p+6), b8=b(p+8), b9=b(p+9), b10=b(p+10), b11=b(p+11), b12=b(p+12), raw=rom[p:p+16].hex(' ', 2))
if __name__ == '__main__':
    for t, tab in sorted(THUNKS.items()):
        print('thunk %x' % t)
        for ch in range(4):
            hdr = tab + sw(tab + 2 * ch)
            fr = anim(hdr)
            s = []
            for f in fr:
                if f[0] == 'loop': s.append('loop->%x' % f[1])
                else:
                    r = framerec(f[1]); s.append('%d/%02x h%d a%d' % (f[2], f[3], r['hurt'], r['atk']))
            print('  ch%d hdr %x:' % (ch, hdr), ' | '.join(s))
