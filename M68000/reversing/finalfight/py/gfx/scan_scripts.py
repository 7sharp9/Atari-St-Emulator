"""scan_scripts.py: find every animation script start the program ROM hands to the script starters `$3b10`/`$3b1c`
(jsr/jmp abs.w) by the forms `lea d(PC),A1` / `lea abs.l,A1` / `movea.l #imm,A1` within the 24 bytes before the call,
the 3-pointer thunk form `movea.l 6(PC,D0.w),A1` (the three words after the call are... the long table that follows) and
the per-character word-table thunk `lea 6(PC),A1 / jmp $3b10` (tables of 4 words).  Prints counts and writes
scripts.json next to the outputs (address -> source).  Used by sheets.py."""
import json, os, sys
import ffframes as F
from cpsgfx import OUT

rom = F.rom
res = {}      # script address -> list of (kind, call address)


def add(a, how, at):
    if 0 < a < len(rom) - 4:
        res.setdefault(a, []).append((how, at))


for starter in (0x3b1c, 0x3b10):
    pat = (0x4eb8, 0x4ef8)
    for i in range(0, len(rom) - 4, 2):
        if F.w(i + 2) != starter or F.w(i) not in pat:
            continue
        call = i
        # long-table form: movea.l 6(PC,D0.w),A1 ; jmp $3b1c ; then three longs (Guy, Cody, Haggar) at call+4..: D0 = 4*char
        if F.w(call - 4) == 0x227b and F.w(call - 2) == 0x0006:
            for c in range(3):
                add(F.l(call + 4 + 4 * c), "tab3[%d]" % c, call)
            continue
        found = False
        for back in range(2, 26, 2):
            p = call - back
            op = F.w(p)
            if op == 0x43fa:                                  # lea d(PC),A1
                d = F.sw(p + 2)
                tgt = p + 2 + d
                if starter == 0x3b10 and back == 4 and d == 6:          # per-character word table follows the jmp
                    t = call + 4
                    for c in range(4):
                        add(t + F.sw(t + 2 * c), "wtab[%d]" % c, call)
                    found = True
                else:
                    add(tgt, "lea pc", call); found = True
                break
            if op == 0x43f9:
                add(F.l(p + 2), "lea abs", call); found = True; break
            if op == 0x227c:
                add(F.l(p + 2), "movea imm", call); found = True; break
        if not found:
            add(-1, "unknown form", call)
good = {}
for a, srcs in sorted(res.items()):
    if a < 0:
        continue
    frames, loop = F.script(a)
    ok = len(frames) > 0 and all(F.frame_ok(b) for (_, b, _, _) in frames) and (loop is not None or len(frames) < 190)
    good[a] = dict(src=srcs, ok=ok, n=len(frames), loop=loop)
n_ok = sum(1 for v in good.values() if v["ok"])
print("script starts found:", len(good), " plausible (every frame block passes frame_ok):", n_ok)
print("unknown call forms:", len(res.get(-1, [])), [hex(x[1]) for x in res.get(-1, [])][:20])
os.makedirs(OUT, exist_ok=True)
json.dump({hex(a): v for a, v in good.items()}, open(os.path.join(OUT, "scripts.json"), "w"), default=str)
