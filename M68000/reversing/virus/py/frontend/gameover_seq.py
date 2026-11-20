"""gameover_seq.py: order of the game-over / hall-of-fame / title / next-demo routines from death/long7.snap (stopped at $25ba0, last life).
Chains `bp <addr> <cap>` through the expected routine entries (one REPL, one variable: the order), printing the step count at each stop
and the cumulative steps. Snapshots at the hall-of-fame page ($26048) and the title page ($24c82) go under $VIRUS_WORK/frontend/gate/.
Usage: gameover_seq.py [snap]"""
import os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from fcommon import run, ROOT, WORK, OUT
snap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "demo", "death", "long7.snap")
GATE = os.path.join(OUT, "gate"); os.makedirs(GATE, exist_ok=True)
seq = [("25ba0", "Lives decrement (stopped here)"), ("25bc0", "Game_Over_Quit"), ("25c14", "bra to GameOver_Screen"), ("25e44", "GameOver_Screen"), ("260f4", "ScoreCode_Print (demo returns at $26178)"),
       ("25e60", "hall-of-fame qualify test"), ("25ebe", "draw 'Scores which I have deigned...'"), ("25f04", "high-score update test ($62a5f)"),
       ("25f3c", "name-entry test"), ("2607c", "demo: stock name"), ("26048", "wait for key / timeout (1f7ee)"), ("2605e", "timeout branch"),
       ("230a4", "Game_Restart"), ("24baa", "Title_AttractLoop"), ("24d14", "attract timer sets demo flag"), ("24d28", "camera climbed past $3200"), ("230c0", "Game_Start (next demo)")]
cmds = []
for a, _ in seq[1:]:
    cmds.append(f"bp {a} 60000000")
    if a == "26048": cmds.append(f"snap {GATE}/hof.snap")
    if a == "24baa": cmds.append(f"s 400000"); cmds.append(f"snap {GATE}/title_after.snap")
out = run(snap, cmds)
tot = 0
for m in re.finditer(r"breakpoint \$([0-9a-f]+) hit \(\d+/\d+\) after (\d+) step", out):
    tot += int(m.group(2)); name = dict(seq).get(m.group(1).lstrip("0"), "?")
    print(f"${m.group(1)[-6:]}  +{m.group(2):>10} steps  cum {tot:>11}  {name}")
for l in out.splitlines():
    if "cap" in l.lower() and "bp" in l.lower() or "not reached" in l.lower(): print(l)
