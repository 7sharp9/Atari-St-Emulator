"""Run every proven-trigger drive twice from its start snapshot and cmp the output snapshots.
Scripts are generated here (labelled pokes in comments). Output: $OUT/drive/<name>_{1,2}.snap, <name>.log
usage: run_all.py [name ...]   (default all)"""
import os, sys, hashlib
from btsec import *
SYS = os.path.join(WORK, "agents", "systems")
PLAY = os.path.join(WORK, "play_start.snap")
D = os.path.join(OUT, "drive"); os.makedirs(D, exist_ok=True)
def snap(name, run): return os.path.join(D, "%s_%d.snap" % (name, run))
# name -> (start snapshot, script template with {S} for the output snapshot, description)
DRIVES = {
 # POKE: hero longword $1f014 = x<<16|y := (1880,464), the level-1 door-in trigger cell ($1b at (1880,464))
 "door_in": (PLAY, "w 1f014 075801d0\ns 3650000\nm 1f014 4\nm 17842 2\nm ff8240 32\nsnap {S}\nquit\n"),
 # POKE: hero := (1000,128), the level-1 door-out cell ($1c), starting from the dungeon snapshot
 "door_out": (os.path.join(D, "door_in_1.snap"), "w 1f014 03e80080\ns 3150000\nm 1f014 4\nm 17842 2\nm 1eff2 8\nm ff8240 32\nsnap {S}\nquit\n"),
 # POKE: hero := (1400,294), 10 px above the level-1 checkpoint ($1f at (1400,304))
 "checkpoint": (PLAY, "w 1f014 05780126\ns 200000\nm 1eff2 4\nsnap {S}\nquit\n"),
 "checkpoint_control": (PLAY, "s 200000\nm 1eff2 4\nsnap {S}\nquit\n"),
 # level skip: joystick 1 = $85, ClrHome ($47), Return ($1c). No pokes.
 "levelskip": (PLAY, "kbd ff 85\ns 100000\nkbd 47\ns 200000\nkbd c7\ns 100000\nkbd ff 00\ns 100000\nm 17826 2\nkbd 1c\ns 100000\nkbd 9c\ns 3000000\nm 17846 2\nsnap {S}\nquit\n"),
 "levelskip_control_nojoy": (PLAY, "kbd 47\ns 200000\nkbd c7\ns 100000\nm 17826 2\nkbd 1c\ns 100000\nkbd 9c\ns 3000000\nm 17846 2\nsnap {S}\nquit\n"),
 # pause: P ($19) then census of the frame body $c900 and the pause loop $cac4 over 600k steps
 "pause": (PLAY, "kbd 19\ns 150000\nkbd 99\nhits 600000 c900 cac4\nsnap {S}\nquit\n"),
 "pause_control": (PLAY, "s 150000\nhits 600000 c900 cac4\nsnap {S}\nquit\n"),
 # ending: POKE $1eeb8 := 1 (level-exit-reached flag) at level index 7 with the boss slot $1f020 empty
 "ending": (os.path.join(SYS, "lvl7.snap"), "w 1eeb8 00010000\nbp c7e6 80000000\nsnap {S}\nquit\n"),
}
def main():
    names = sys.argv[1:] or list(DRIVES)
    for n in names:
        start, tmpl = DRIVES[n]
        hs = []
        for run in (1, 2):
            if n == "door_out" and not os.path.exists(start): continue
            out = run_repl(start, tmpl.format(S=snap(n, run)), os.path.join(D, "%s_%d.log" % (n, run)))
            hs.append(hashlib.md5(open(snap(n, run), "rb").read()).hexdigest())
        print("%-24s run1 %s run2 %s %s" % (n, hs[0][:10], hs[1][:10] if len(hs) > 1 else "-", "IDENTICAL" if len(set(hs)) == 1 else "DIFFERENT"))
if __name__ == "__main__": main()
