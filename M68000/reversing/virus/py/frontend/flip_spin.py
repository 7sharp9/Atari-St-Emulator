"""flip_spin.py [snap]: the frame-routine proofs for Screen_FlipSetscreen $183f2 and SpinMatrices_Update $2617a, from the flight
snapshot $VIRUS_WORK/fl/f1.snap, 1,200,000 steps each (one REPL per run).
  flip : `hits` on the main loop, the flip, its Setscreen trap and the score check; `watch 2705e 4` counts writes by PC
         (control: the no-trap flip $18430/$18448 has 0 hits).
  spin : `watch 270ec 54` counts writes to the three matrices by PC; control: the same run with `ww 2617a 4e75` (a labelled poke:
         an rts at the routine's entry) has 0 writes.
Output: the counts, then 'flip ok' / 'spin ok' lines."""
import os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fcommon import run, WORK
snap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "fl", "f1.snap")
out = run(snap, ["hits 1200000 23198 183f2 18428 18430 18410 18448 2617a 24956 231c0 179f6 17a1c"])
h = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$0*([0-9a-f]+)\s+(\d+)\s+first", out)}
print("hits:", {k: h.get(k) for k in ("23198", "183f2", "18428", "18410", "2617a", "24956", "231c0", "18430", "18448", "179f6", "17a1c")})
w = run(snap, ["watch 2705e 4", "s 1200000"])
c = collections.Counter(re.findall(r"pc=\$0*([0-9a-f]+) WriteWord \$0002705e", w))
print("watch 2705e writes by pc:", dict(c))
n = h["183f2"]
print(f"flip ok: {n} frames, {n} Setscreen traps, {c.get('1840a', 0)} writes of $2705e by $1840a, no-trap flip hits {h.get('18430')}+{h.get('18448')}" if
      n > 0 and n == h["23198"] == h["18428"] == c.get("1840a", 0) and h.get("18430") == 0 == h.get("18448") else "flip FAIL")
w1 = run(snap, ["watch 270ec 54", "s 1200000"])
c1 = collections.Counter(re.findall(r"WATCH: step=\d+ pc=\$0*([0-9a-f]+)", w1))
w0 = run(snap, ["ww 2617a 4e75", "watch 270ec 54", "s 1200000"])
n0 = len(re.findall(r"WATCH:", w0))
fr = h["2617a"]
print(f"spin writes: {sum(c1.values())} at {len(c1)} pcs ({set(c1.values())} each); frames {fr}; control (rts stub poke) writes: {n0}")
print(f"spin ok: 9 store pcs x {3 * fr} (3 matrices x {fr} frames) = {sum(c1.values())} writes, control 0" if set(c1.values()) == {3 * fr} and len(c1) == 9 and n0 == 0 else "spin FAIL")
