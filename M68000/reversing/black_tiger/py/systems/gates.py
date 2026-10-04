"""Gates for system.md.  usage: gates.py container|btsnd|demo|timera|frames|protection|all
Each prints PASS/FAIL lines with counts.  Needs the BT_WORK snapshots (see btcommon.py) and the emulator DLL.
 container  : file byte b of COMMAND.PRG equals game byte b+$c228 in the running image (24-byte windows free of relocations)
 btsnd      : BTSND header = 32 (offset,length) entries, entries 1..8 contiguous to the file size, 9..31 repeat entry 8
 demo       : 65 frames from attract/a_gameon.snap read 65 demo bytes (hits $f358 == hits $f37c == index delta)
 timera     : at the title (tl/t24.snap) hits of $106c2 == fall of the sample counter $3157e == rise of pointer $31582 over 1M steps;
              in play_start.snap the ISR never runs
 frames     : 49 consecutive game frames of 3M steps span exactly 5 VBLs each (events log)
 protection : $f52e is `moveq #0,D0 / rts`, no instruction in the image calls $f532
"""
import os, re, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from btcommon import *

def snap_mem(path, addr, n): return ram_from_snap(path)[addr:addr + n]

def container():
    f = open(f"{WORK}/files/COMMAND.PRG", "rb").read()
    ram = ram_from_snap(f"{WORK}/play_start.snap")
    ok = tot = 0
    for a in range(0xc470 + 0x4000, 0x1f274 - 24, 0x400):
        w = ram[a:a + 24]
        tot += 1
        off = a - 0xc228
        if f[off:off + 24] == w: ok += 1
    print(("PASS" if ok > 0.5 * tot else "FAIL"), f"container: {ok}/{tot} sampled 24-byte windows match at file offset a-$c228 "
          "(misses are windows that hold relocated longs)")
    print("PASS" if f[0xb389:0xb389 + 18] == b"Please insert Disk" and ram[0x175b1:0x175b1 + 18] == b"Please insert Disk" else "FAIL",
          "container: 'Please insert Disk' at file $b389 == runtime $175b1")

def btsnd():
    d = open(f"{WORK}/files/BTSND", "rb").read()
    end, good = 0x100, 0
    for i in range(1, 9):
        o, l = struct.unpack(">II", d[i * 8:i * 8 + 8]); good += (o == end); end = o + l
    dup = sum(struct.unpack(">II", d[i * 8:i * 8 + 8]) == struct.unpack(">II", d[64:72]) for i in range(8, 32))
    print("PASS" if good == 8 and end == len(d) and dup == 24 else "FAIL", f"btsnd: contiguous entries {good}/8, end ${end:x} vs size ${len(d):x}, entries 8..31 identical {dup}/24")

def demo():
    s = f"{OUT}/attract/a_gameon.snap"
    out = run_repl(s, "hits 6000000 f358 f37c\nm 1784c 2\nquit\n")
    h = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$00(f358|f37c)\s+(\d+)", out)}
    idx0 = struct.unpack(">H", snap_mem(s, 0x1784c, 2))[0]
    idx1 = int(re.findall(r"^([0-9a-f]{2} [0-9a-f]{2})$", out, re.M)[-1].replace(" ", ""), 16)
    print("PASS" if h["f358"] == h["f37c"] == idx1 - idx0 else "FAIL", f"demo: hits f358={h['f358']} f37c={h['f37c']} index ${idx0:x}->${idx1:x} (+{idx1 - idx0})")

def timera():
    for snap, want in ((f"{WORK}/tl/t24.snap", True), (f"{WORK}/play_start.snap", False)):
        out = run_repl(snap, "m 3157e 4\nm 31582 4\nhits 1000000 106c2\nm 3157e 4\nm 31582 4\nquit\n")
        rows = [int(r.replace(" ", ""), 16) for r in re.findall(r"^((?:[0-9a-f]{2} ){3}[0-9a-f]{2})$", out, re.M)]
        n = int(re.search(r"\$0106c2\s+(\d+)", out).group(1))
        c0, p0, c1, p1 = rows[:4]
        if want: print("PASS" if n == c0 - c1 == p1 - p0 and n > 0 else "FAIL", f"timera title: ISR hits {n}, count fell {c0 - c1}, pointer rose {p1 - p0}")
        else: print("PASS" if n == 0 else "FAIL", f"timera play: ISR hits {n}")

def frames():
    import bisect
    from evt_stats import load
    p = f"{OUT}/ev/play3M.evt"
    if not os.path.exists(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        run_repl(f"{WORK}/play_start.snap", "s 3000000\nquit\n", {"ATARI_TRACE_EVENTS": p})
    st, recs = load(p)
    fl = [r[0] for r in recs if r[4] == 3 and r[2] == 0xaad8]
    vb = [r[0] for r in recs if r[4] == 6 and r[2] == 0xfc0634]
    v = [bisect.bisect_left(vb, b) - bisect.bisect_left(vb, a) for a, b in zip(fl, fl[1:])]
    print("PASS" if v and all(x == 5 for x in v[:49]) else "FAIL", f"frames: {sum(x == 5 for x in v)}/{len(v)} frame gaps are exactly 5 VBLs")

def protection():
    ram = ram_from_snap(f"{WORK}/play_start.snap")
    stub = ram[0xf52e:0xf532] == bytes.fromhex("70004e75")
    import subprocess
    lst = f"{OUT}/cmd_play.asm"
    n = sum(1 for l in open(lst) if re.search(r"(bsr|jsr|jmp|bra)\s+\$f532\b", l))
    print("PASS" if stub and n == 0 else "FAIL", f"protection: $f52e stub bytes {ram[0xf52e:0xf532].hex()} callers of $f532 in listing: {n}")

if __name__ == "__main__":
    for g in (sys.argv[1:] or ["all"]):
        for fn in (container, btsnd, demo, timera, frames, protection) if g == "all" else (globals()[g],):
            fn()
