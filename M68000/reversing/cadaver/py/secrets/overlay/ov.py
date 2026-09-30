"""ov.py: thin helpers over reversing/cadaver/py/secrets/repl.py for the overlay proofs.  ATARI_NOTRACE=1 is set by Repl.
wb/ww(r, addr, val) write ONE byte / word (patch inside the even-aligned longword: REPL `w` is a longword and crashes on an odd address).
a5(off) -> absolute address of (A5)+off."""
import sys, os
sys.path.insert(0, 'reversing/cadaver/py/secrets')
from repl import Repl, A5
def a5(off): return A5 + off
def wb(r, addr, val):
    """one byte; REPL `w` dies on an odd address, so patch inside the even-aligned longword"""
    base = addr & ~1; cur = bytearray(r.mem(base, 4)); cur[addr - base] = val & 0xff
    r.cmd('w %x %s' % (base, cur.hex()))
def ww(r, addr, val):
    base = addr & ~1; cur = bytearray(r.mem(base, 4)); cur[addr - base] = (val >> 8) & 0xff; cur[addr - base + 1] = val & 0xff
    r.cmd('w %x %s' % (base, cur.hex()))
def wl(r, addr, val): r.cmd('w %x %08x' % (addr, val & 0xffffffff))
