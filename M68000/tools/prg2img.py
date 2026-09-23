#!/usr/bin/env python3
"""Relocate a GEMDOS executable (.PRG/.TOS/.APP, magic $601a) to a load address and
write TEXT+DATA followed by a zeroed BSS: the program image exactly as TOS lays it out
in RAM, minus the basepage.

The load address is the runtime TEXT start (basepage + $100), which an
`ATARI_TRACE_GEMDOS=1` run prints on its Pexec line ("text=$..."). With that base every
address in the image equals a runtime address, so the image can be fed to
`disassemble.py --rom img --base <text>` or imported into Ghidra as a raw binary at the
same base (tools/ghidra/DecompileAll.java) and line up with traces and snapshots.

    python tools/prg2img.py POPULOUS.GOD pop_ad58.img ad58
"""
import argparse
import struct


def relocate(prg: bytes, base: int) -> tuple[bytearray, dict]:
    magic, tl, dl, bl, sl = struct.unpack_from('>HIIII', prg, 0)
    if magic != 0x601a:
        raise SystemExit(f"not a GEMDOS executable (magic ${magic:04x})")
    img = bytearray(prg[28:28 + tl + dl]) + bytearray(bl)
    r = 28 + tl + dl + sl                     # relocation table follows the symbols
    first = struct.unpack_from('>I', prg, r)[0]
    r += 4
    n = 0
    if first:
        p = first
        while True:
            v = struct.unpack_from('>I', img, p)[0]
            struct.pack_into('>I', img, p, (v + base) & 0xffffffff)
            n += 1
            step = 0
            while True:                       # 1 = advance 254 and keep reading; 0 = end
                b = prg[r]; r += 1
                if b == 0 or b != 1:
                    step += b
                    break
                step += 254
            if b == 0:
                break
            p += step
    return img, dict(text=tl, data=dl, bss=bl, sym=sl, relocs=n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('prg')
    ap.add_argument('out')
    ap.add_argument('base', help='runtime TEXT address, hex')
    a = ap.parse_args()
    img, info = relocate(open(a.prg, 'rb').read(), int(a.base, 16))
    open(a.out, 'wb').write(img)
    print('text $%(text)x data $%(data)x bss $%(bss)x sym $%(sym)x relocs %(relocs)d' % info)


if __name__ == '__main__':
    main()
