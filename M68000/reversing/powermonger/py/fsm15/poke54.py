"""poke54.py: labelled pokes of the $54 lord loop ($15b00) from one natural entry snapshot (cap/rand1_1.snap, stopped at $15ada,
merchant A1=$52f84, settlement $4fcbe, home lord 7 (offset $e0), D2 = 14(A1) & 7 = 5, A4 offset $4f914 = $1c0, the first free slot).

Arms (each a REPL longword `w`, the neighbouring bytes rewritten unchanged):
  ctl    no poke
  last   settlement word 14 ($4fcbe+14) $00e0 -> $01a0: home = lord 13, the last allocated record (A4 - 32)
  atA4   settlement word 14 $00e0 -> $01c0: home = the slot at A4 (nation 0, unallocated): the only way into $15b14
  hang   lord 7 nation byte $4e5f4 $02 -> $00 (home stays lord 7, below A4)
Per arm: run 1 `u 15b54 3000000`, `r`, `u 15b5a`, `m A1 50`; run 2 `hits 150 15b00 15b14 15b1c` (3000000 for hang; 150 steps
covers this entry's loop and stops before the next merchant's entry).  The model (gate54.model) predicts
A3, A0, passes, the wrap and the merchant record; the hang arm predicts no exit.

    cd M68000; uv run python reversing/powermonger/py/fsm15/poke54.py
"""
import os, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate54 as G

SNAP = f"{os.environ.get('PM_WORK', 'scratchpad/pm162')}/merchant/cap/rand1_1.snap"
A1 = 0x52f84
ARMS = {"ctl": [], "last": [(0x4fcbe + 14, "01a00000")], "atA4": [(0x4fcbe + 14, "01c00000")], "hang": [(0x4e5f4, "000203a8")]}
OLD = {0x4fcbe + 14: "00e00000", 0x4e5f4: "020203a8"}


def main():
    base = (G.ROOT / SNAP.replace(".snap", ".ram")).read_bytes()
    for arm, pokes in ARMS.items():
        r = bytearray(base)
        for a, v in pokes:
            assert base[a:a + 4].hex() == OLD[a], (arm, hex(a), base[a:a + 4].hex())
            r[a:a + 4] = bytes.fromhex(v)
        A3, A0, A4, passes, wrapped, mm = G.model(bytes(r), A1)
        pk = [f"w {a:x} {v}" for a, v in pokes]
        log1 = G.repl(SNAP, pk + ["u 15b54 3000000", "r", "u 15b5a 200000", f"m {A1:x} 50"])
        log2 = G.repl(SNAP, pk + [f"hits {3000000 if arm == 'hang' else 150} 15b00 15b14 15b1c"])
        reg = {k: int(v, 16) for k, v in re.findall(r"\b(A[034]):([0-9a-f]{8})", log1)}
        reached = re.findall(r"reached PC=\$000(15b54|15b5a)", log1)
        h = {a: int(n) for a, n in re.findall(r"\$0(15b00|15b14|15b1c)\s+(\d+)", log2)}
        d = G.dumps(log1)
        if A3 is None:
            ok = reached == [] and h.get("15b1c") == 0
            print(f"{arm:5s} model: no exit ({passes}+ passes) | emu: reached {reached}, hits $15b00 {h.get('15b00')} $15b14 {h.get('15b14')} "
                  f"$15b1c {h.get('15b1c')} over 3M steps -> {'MATCH' if ok else 'MISMATCH'}")
            continue
        rec_ok = bool(d) and d[-1] == bytes(mm[A1:A1 + 50])
        ok = (reached == ["15b54", "15b5a"] and reg.get("A3") == A3 and reg.get("A0") == A0 and rec_ok
              and h.get("15b14") == int(wrapped) and h.get("15b00") == passes and h.get("15b1c") == 1)
        print(f"{arm:5s} model: A3=${A3:x} (lord {(A3 - G.LEADER) // 32}) A0=${A0:x} passes={passes} wrap={int(wrapped)} 46(A1)=${mm[A1+46]<<8|mm[A1+47]:x}"
              f" | emu: A3=${reg.get('A3', 0):x} A0=${reg.get('A0', 0):x} hits $15b00 {h.get('15b00')} $15b14 {h.get('15b14')} $15b1c {h.get('15b1c')}"
              f" rec50 {'=' if rec_ok else '!='} -> {'MATCH' if ok else 'MISMATCH'}")


if __name__ == "__main__":
    main()
