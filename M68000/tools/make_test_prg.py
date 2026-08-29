#!/usr/bin/env python3
"""Emit a trivial, hand-assembled GEMDOS .PRG for exercising the disk-load path.

The program (18 bytes of TEXT, no DATA/BSS, no relocations):

    start:  moveq   #10,d0          ; 700A
    loop:   bsr.w   sub             ; 6100 000A
            dbf     d0,loop         ; 51C8 FFFA
            clr.w   -(sp)           ; 4267   \\ GEMDOS Pterm0
            trap    #1              ; 4E41   /
    sub:    nop                     ; 4E71
            rts                     ; 4E75

A counted loop calling a subroutine, then a clean Pterm0 - enough for the trace
event log to show real basic blocks, a back-edge and a call/return on loaded code.
"""
import struct
import sys

TEXT = bytes.fromhex("700A" "6100000A" "51C8FFFA" "4267" "4E41" "4E71" "4E75")
assert len(TEXT) == 18


def build() -> bytes:
    h = bytearray(28)
    struct.pack_into(">H", h, 0, 0x601A)   # magic
    struct.pack_into(">I", h, 2, len(TEXT))  # tsize
    struct.pack_into(">I", h, 6, 0)          # dsize
    struct.pack_into(">I", h, 10, 0)         # bsize
    struct.pack_into(">I", h, 14, 0)         # ssize
    struct.pack_into(">I", h, 18, 0)         # reserved
    struct.pack_into(">I", h, 22, 0)         # prgflags
    struct.pack_into(">H", h, 26, 0)         # absflag (0 = relocation table present)
    reloc = struct.pack(">I", 0)             # no fixups
    return bytes(h) + TEXT + reloc


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "TEST.PRG"
    data = build()
    open(out, "wb").write(data)
    print(f"Wrote {out}: {len(data)} bytes (28 header + {len(TEXT)} text + 4 reloc)")
