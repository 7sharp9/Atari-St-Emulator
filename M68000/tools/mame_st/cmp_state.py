#!/usr/bin/env python3
"""Compare the F# core's idle-desktop RAM (from a .snap) with MAME st_uk's RAM dump (boot2.lua).
usage: tools/mame_st/cmp_state.py <fsharp.snap> <mame out dir> <frame>   (run with M68000/.venv/bin/python)"""
import sys, os, struct
root = os.path.abspath(__file__)
while not os.path.exists(os.path.join(root, "tools", "rdis.py")):
    root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, "tools"))
from gfxview import load_ram, load_video_regs
snap, od, fr = sys.argv[1], sys.argv[2], sys.argv[3]
F, _ = load_ram(snap); regs = load_video_regs(snap)
M = open(f"{od}/ram_f{fr}.bin", "rb").read()
Mscr = open(f"{od}/screen_f{fr}.bin", "rb").read()
Mpal = struct.unpack(">16H", open(f"{od}/pal_f{fr}.bin", "rb").read())
assert len(F) == len(M) == 0x100000, (len(F), len(M))
def l(b, a): return struct.unpack(">I", b[a:a+4])[0]
def w(b, a): return struct.unpack(">H", b[a:a+2])[0]
def eq(a, b, lo, hi):
    n = sum(1 for i in range(lo, hi) if a[i] == b[i]); return n, hi - lo
print("region                         equal/total")
for name, lo, hi in [("vectors $0-$3ff", 0, 0x400), ("sysvars $400-$5ff", 0x400, 0x600), ("$600-$7ff", 0x600, 0x800),
                     ("RAM $800-$f7fff (OS/bss/heap)", 0x800, 0xf8000), ("screen RAM $f8000-$fffff", 0xf8000, 0x100000), ("all 1MB", 0, 0x100000)]:
    n, t = eq(F, M, lo, hi); print(f"{name:34s} {n}/{t}")
print("F# base/pal:", hex(regs["base"]), [hex(x) for x in regs["palette_words"]])
print("MAME pal   :", [hex(x) for x in Mpal])
print("palette equal:", sum(1 for a, b in zip(regs["palette_words"], Mpal) if (a & 0x777) == (b & 0x777)), "/16  (compared & $777)")
fb = regs["base"]; Fscr = F[fb:fb+32000]
n = sum(1 for a, b in zip(Fscr, Mscr) if a == b); print("screen RAM bytes equal (at each v_bas_ad):", n, "/ 32000")
# rows that differ
rows = sorted({i // 160 for i in range(32000) if Fscr[i] != Mscr[i]}); print("differing scan lines:", len(rows), rows[:40])
print("\nvectors that differ ($0-$3ff, longword view):")
for a in range(0, 0x400, 4):
    if F[a:a+4] != M[a:a+4]: print(f"  ${a:03x} (vec {a//4:3d}) F#={l(F,a):08x} MAME={l(M,a):08x}")
print("\nsysvars $400-$5ff longword differences:")
for a in range(0x400, 0x600, 4):
    if F[a:a+4] != M[a:a+4]: print(f"  ${a:03x} F#={l(F,a):08x} MAME={l(M,a):08x}")
print("\nselected sysvars (F# / MAME):")
names = {0x42e:"phystop",0x432:"membot",0x436:"memtop",0x43a:"memvalid",0x43e:"flock(w)",0x44e:"_v_bas_ad",0x4a2:"savptr",0x4a6:"_nflops(w)",0x4ba:"_hz_200",0x466:"_frclock",0x4c2:"_drvbits",0x4c6:"_dskbufp",0x4f2:"_sysbase",0x4fa:"end_os",0x4fe:"exec_os",0x516:"?"}
for a, n in sorted(names.items()):
    if "(w)" in n: print(f"  ${a:03x} {n:12s} {w(F,a):04x} / {w(M,a):04x}")
    else: print(f"  ${a:03x} {n:12s} {l(F,a):08x} / {l(M,a):08x}")
