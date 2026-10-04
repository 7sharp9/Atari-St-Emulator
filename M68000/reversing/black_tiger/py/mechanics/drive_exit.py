"""Level exit -> boss -> level clear -> next level, driven from play_start.snap (level 1). Labelled pokes:
  1. hero position longword $1f014 := (x=1864, y=304)  = the exit object (kind $20) cell in special_items.txt (levels_collision.png)
  2. both boss records $1f020 / $1f030 := type 1, state 4 (dying), animation $30 (finishes at once; the same poke as killscore_check)
  3. one key press (scancode $39 down / $b9 up) at the 'Please insert Disk B' prompt (service $15 blocks on a key)
Prints, after each phase: exit flag $1eeb8, boss slot $1f020 (type, state, x, y, hp), money, level index $17846, map size $201c8, hero x,y.
Expected: exit flag 1 and boss hp $10 at (2032,304) after phase 1; money 200 -> 500 (bonus 300) and level index still 0 at the prompt;
level index 1, map 128x64 and hero at (160,944) (level 2 anchor A) after the key."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
E = os.path.join(b.OUT, "snaps")
def rows(out):
    return [[int(x, 16) for x in l.split()] for l in out.splitlines() if re.fullmatch(r"([0-9a-f]{2} ?)+", l.strip())]
p1 = ["w 1f014 07480130", "s 600000", "m 1f020 10", "m 1eeb8 2", "m 1f002 2", "snap %s/exit_a.snap" % E]
r = rows(b.repl(snap, p1))
w = lambda v, i: (v[i] << 8) | v[i + 1]
print("phase 1 (exit touched): exit flag %d, boss slot type %d state %d x %d y %d hp %d, money %d" % (w(r[1], 0), r[0][0], r[0][1], w(r[0], 4), w(r[0], 6), r[0][8], w(r[2], 0)))
p2 = ["w 1f020 01043000", "w 1f030 01043000", "s 4500000", "m 1f002 2", "m 17846 2", "snap %s/clear_b.snap" % E, "kbd 39", "s 100000", "kbd b9", "s 2500000",
      "m 1f002 2", "m 17846 2", "m 201c8 4", "m 1f014 4"]
out = b.repl(os.path.join(E, "exit_a.snap"), p2)
r = rows(out)
print("phase 2 (bosses killed, bonus, prompt): money %d level index %d" % (w(r[0], 0), w(r[1], 0)))
print("phase 3 (after the key): money %d level index %d map %dx%d hero (%d,%d)" % (w(r[2], 0), w(r[3], 0), w(r[4], 0), w(r[4], 2), w(r[5], 0), w(r[5], 2)))
