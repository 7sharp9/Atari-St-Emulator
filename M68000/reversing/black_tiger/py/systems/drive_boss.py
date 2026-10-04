"""Boss drive: for each level index 0..7 start from the level's start snapshot, move the hero onto the LEVEL EXIT
cell (map object kind $20, `agents/mechanics/special_items.txt`), and let the game fire its own exit routine $cfa4
(hero within 32 px: sets $1eeb8, clears actor records from $1f020, loads the boss bank per table $17226 via
trap #3 service 9, spawns the boss in slot $1f020).

LABELLED POKE (the only one): `w 1f014 <x:4 hex><y:4 hex>` = hero x word $1f014 and y word $1f016 := exit cell.
Start snapshots: level 0 = play_start.snap; levels 1..7 = agents/systems/lvl<k>.snap (built-in level skip, see
drive_levels.py; hero untouched).  Pass 1 steps 30,000 at a time until $1eeb8 != 0 (frame granularity), pass 2
repeats the run to that exact step and writes boss<L>_trigger.snap, then +FIGHT steps -> boss<L>_fight.snap.

usage: drive_boss.py [levels=0-7] [fight_steps=1500000]
outputs $OUT/boss/boss<L>_trigger.snap/.png, boss<L>_fight.snap/.png, boss/boss_table.txt (tab separated)
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from btcommon import *
import subprocess

BOSSDIR = os.path.join(OUT, "boss")
def parse_m(out):
    # "m" prints bytes as hex lines; collect lines made only of 2-digit hex pairs
    return [l.split() for l in out.splitlines() if re.fullmatch(r"([0-9a-f]{2} )*[0-9a-f]{2}", l.strip())]

def poke_line(x, y): return f"w 1f014 {x:04x}{y:04x}"

def drive(level, fight):
    ex = exits()[level]
    snap = level_snap(level)
    # pass 1: find the first 30,000-step checkpoint with $1eeb8 != 0
    sc = [poke_line(*ex)] + ["s 30000", "m 1eeb8 2"] * 60 + ["quit"]
    rows = parse_m(run_repl(snap, "\n".join(sc) + "\n"))
    n = next((i + 1 for i, r in enumerate(rows) if r != ["00", "00"]), None)
    if n is None: return None
    steps = n * 30000
    # pass 2: exact reproduction, snapshots and state dumps
    t, f = f"{BOSSDIR}/boss{level}_trigger.snap", f"{BOSSDIR}/boss{level}_fight.snap"
    sc = [poke_line(*ex), f"s {steps}", f"snap {t}", "m 17846 2", "m 1f020 32", "m 1f010 16", f"s {fight}", f"snap {f}", "m 1f020 32", "m 1f010 16", "m 1eeb8 2", "quit"]
    out = run_repl(snap, "\n".join(sc) + "\n", {"ATARI_TRACE_GEMDOS": "1", "ATARI_TRACE_OS": "1"})
    files = re.findall(r'Fopen\("([^"]+)"', out)
    rows = parse_m(out)
    # rows: [0]=level, [1]=slot1 at trigger (32 bytes = slots 1,2), [2]=hero, [3]=slot1+2 at fight, [4]=hero at fight, [5]=$1eeb8
    fr = rows[3] if len(rows) > 5 else []
    return dict(level=level, exit=ex, steps=steps, files=",".join(files) or "-", slot1=" ".join(fr[:16]),
                hero=" ".join(rows[4][:8]) if len(rows) > 5 else "", flag=" ".join(rows[5]) if len(rows) > 5 else "")

if __name__ == "__main__":
    lv = sys.argv[1] if len(sys.argv) > 1 else "0-7"
    levels = list(range(int(lv.split("-")[0]), int(lv.split("-")[-1]) + 1))
    fight = int(sys.argv[2]) if len(sys.argv) > 2 else 1500000
    os.makedirs(BOSSDIR, exist_ok=True)
    rows = []
    for L in levels:
        r = drive(L, fight)
        print(L, r)
        if r: rows.append(r)
        for k in ("trigger", "fight"):
            p = f"{BOSSDIR}/boss{L}_{k}.snap"
            if os.path.exists(p):
                subprocess.run([sys.executable, os.path.join(ROOT, "tools", "snap_render.py"), p, p[:-5] + ".png"], capture_output=True)
    with open(BOSSDIR + "/boss_table.txt", "w") as f:
        f.write("level_idx\texit_xy\tsteps_to_trigger\tfopen_after_trigger\tboss_slot_1f020_at_fight\thero_1f010_at_fight\tflag_1eeb8\n")
        for r in rows: f.write(f"{r['level']}\t{r['exit']}\t{r['steps']}\t{r['files']}\t{r['slot1']}\t{r['hero']}\t{r['flag']}\n")
