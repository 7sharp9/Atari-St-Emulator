"""name_strings.py - decode the packed dialogue/UI string table at (A5)+168/172, found this pass
by tracing every caller of $00fd2c (the routine mechanics.md sec18b already named as the
name-banner's string decoder, but never enumerated beyond the couple of indices sec18b's own
call-tree walk touched).

Format, read directly off the disassembly at $00fd2c/$00fd4e/$00fda2 (verified against
room2_tunnel_entry.snap, not inferred): `(A5)+168` is a word-indexed offset table (index*2 ->
16-bit offset), `(A5)+172` is the base the offset is added to, giving the start of a 6-bit-packed
character stream (3 bytes -> 4 chars, the same bit layout as base64: `b0>>2`, `(b0&3)<<4|b1>>4`,
`(b1&0xf)<<2|b2>>6`, `b2&0x3f`). Each 6-bit value indexes a 256-byte character map at the fixed
address `$5ac0`; a map entry of `$ff` is the terminator.

This is a *different* table from the ~40-entry debug-string vocabulary `py/verb_opcode_map.py`
decodes (that one is plain ASCII, referenced by `lea <string>.l,A0`) - this one is the game's own
compressed dialogue/item/spell/monster-name text, never enumerated before this pass. Proven
correct by producing exact, recognisable game text (verb names matching the already-proven
UNLOCK CHEST/CREATE opcodes, and real monster names - DEAD RAT/GIANT RAT/SKELETON - not
guessed or reconstructed).

Known indices (cross-checked against already-proven live objects): 200 = "LEVER" (object id 144's
own live status-bar name), 188 = "BOAT", 197 = "PICKAXE...". These don't equal the objects' own
numeric ids (144/?/?) - there is no known numeric relationship between an object's id and its
name-string index yet; whatever field of the type-6 record holds an object's own name index is
still unidentified (matching mechanics.md's own standing "proximity-icon writer... unidentified
open item").

    python reversing/cadaver/py/name_strings.py <snap> [--lo N] [--hi N] [--grep WORD]

Prints every decodable index in [lo, hi) as raw bytes (embedded NUL/CR bytes and all - many
entries are several messages back to back, only the first is the index's own "primary" string,
later ones are whatever the next index's table entry happens to overlap since the format has no
explicit length field this pass found - read the first line of each entry, not the whole tail).
"""
import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from gfxview import load_ram, snapshot_regs  # noqa: E402

CHARMAP_ADDR = 0x5ac0


def u32(ram, base, addr):
    o = addr - base
    return struct.unpack(">I", ram[o:o + 4])[0]


def u16(ram, base, addr):
    o = addr - base
    return struct.unpack(">H", ram[o:o + 2])[0]


def u8(ram, base, addr):
    return ram[addr - base]


def decode_index(ram, base, t168, t172, index, maxlen=200):
    off = u16(ram, base, t168 + index * 2)
    addr = t172 + off
    out = bytearray()
    while len(out) < maxlen:
        b0 = u8(ram, base, addr)
        b1 = u8(ram, base, addr + 1)
        b2 = u8(ram, base, addr + 2)
        vals = (
            b0 >> 2,
            ((b0 & 0x3) << 4) | (b1 >> 4),
            ((b1 & 0xF) << 2) | (b2 >> 6),
            b2 & 0x3F,
        )
        stop = False
        for v in vals:
            c = u8(ram, base, CHARMAP_ADDR + v)
            if c == 0xFF:
                stop = True
                break
            out.append(c)
        addr += 3
        if stop:
            break
    return bytes(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap")
    ap.add_argument("--lo", type=int, default=0)
    ap.add_argument("--hi", type=int, default=600)
    ap.add_argument("--grep", default=None, help="only print entries containing this substring (case-insensitive)")
    args = ap.parse_args()

    ram, base = load_ram(args.snap)
    regs, _ = snapshot_regs(args.snap)
    a5 = regs["a5"]
    t168 = u32(ram, base, a5 + 168)
    t172 = u32(ram, base, a5 + 172)

    needle = args.grep.encode("ascii").upper() if args.grep else None
    for i in range(args.lo, args.hi):
        try:
            s = decode_index(ram, base, t168, t172, i)
        except (IndexError, struct.error):
            break
        if needle and needle not in s.upper():
            continue
        print(f"{i:4d} {s!r}")


if __name__ == "__main__":
    main()
