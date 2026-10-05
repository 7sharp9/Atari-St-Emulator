"""Crude Buster graphics ROM assembly and decode (pure numpy), from cbuster.cpp ROM_START and gfx_layouts.
Run as a script to check the assembled regions against MAME's own (dumps/region_*.bin).
"""
import os, sys, zipfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))          # agents/gfx
ZIP = os.path.expanduser(os.environ.get("CB_ZIP", "~/mame-roms/cbuster.zip"))


def _rd(z, name):
    return np.frombuffer(z.read(name), dtype=np.uint8)


def assemble(set_prefix=""):
    """Return dict region name -> uint8 array, built from the zip exactly as the ROM_START of `cbuster` says.
    ROM_LOAD16_BYTE(x, 0x80000 / 0x80001): bytes at even/odd offsets.  ROM_LOAD32_WORD(mab-02, 0) /
    (mab-03, 2): 16-bit groups at offset 0 / 2 modulo 4 (little-endian region: file byte order kept inside a group).
    ROM_LOAD32_BYTE(fuNN, 0x100000 + k): byte k of every 4."""
    z = zipfile.ZipFile(ZIP)
    t1 = np.zeros(0x100000, np.uint8)
    t1[0:0x80000] = _rd(z, "mab-00.4c")
    t1[0x80000:0xa0000:2] = _rd(z, "fu05-.6c")
    t1[0x80001:0xa0000:2] = _rd(z, "fu06-.7c")
    t2 = _rd(z, "mab-01.19a").copy()
    sp = np.zeros(0x140000, np.uint8)
    a = _rd(z, "mab-02.10a"); b = _rd(z, "mab-03.11a")
    for i in range(2):                       # byte i of each 16-bit group
        sp[0x000000 + i: 0x100000: 4] = a[i::2]
        sp[0x000002 + i: 0x100000: 4] = b[i::2]
    for k, n in enumerate(["fu07-.4a", "fu08-.5a", "fu09-.7a", "fu10-.8a"]):
        sp[0x100000 + k: 0x140000: 4] = _rd(z, n)
    return {"tiles1": t1, "tiles2": t2, "sprites": sp}


def decode(region, kind):
    """Decode with the MAME layouts.  kind 'char': 8x8, planes {24,16,8,0}, x STEP8(0,1), y STEP8(0,32), 256 bits/tile.
    kind 'tile': 16x16, planes {24,16,8,0}, x {512..519, 0..7}, y STEP16(0,32), 1024 bits/tile.
    Bit numbering is MAME's: bit n is mask 0x80 >> (n & 7) of byte n >> 3.  Returns (n, h, w) uint8 pens 0..15."""
    bits = np.unpackbits(region)                      # MSB first == MAME bit order
    if kind == "char":
        w, h, stride, xoff, yoff = 8, 8, 256, np.arange(8), np.arange(8) * 32
    else:
        w, h, stride = 16, 16, 1024
        xoff = np.concatenate([512 + np.arange(8), np.arange(8)]); yoff = np.arange(16) * 32
    n = len(bits) // stride
    planes = [24, 16, 8, 0]
    base = (np.arange(n, dtype=np.int64) * stride)[:, None, None]
    pix = np.zeros((n, h, w), np.uint8)
    for p, po in enumerate(planes):
        idx = base + po + yoff[None, :, None] + xoff[None, None, :]
        pix |= (bits[idx] << (3 - p)).astype(np.uint8)     # plane 0 is the most significant bit of the pen
    return pix


if __name__ == "__main__":
    r = assemble()
    ok = True
    for name, arr in r.items():
        ref = np.fromfile(os.path.join(ROOT, "dumps", "region_%s.bin" % name), dtype=np.uint8)
        eq = int((arr == ref).sum()); print("region %-8s %d of %d bytes identical to MAME's" % (name, eq, len(ref)))
        ok &= eq == len(ref)
    sys.exit(0 if ok else 1)
