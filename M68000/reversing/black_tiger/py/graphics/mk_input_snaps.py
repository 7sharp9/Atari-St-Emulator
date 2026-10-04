"""mk_input_snaps.py - atk0..7 (fire held) and walk0..9 (joystick right held) from play_start.snap, at page-flip entries."""
from drive import *

def main():
    lines = ["kbd ff 80", "s 30000"]
    for k in range(8):
        lines += ["bp aad8 2000000", "snap %s/atk%d.snap" % (SNAPDIR, k), "s 5000"]
    print("atk", run_repl("play_start.snap", lines).count("state saved"))
    lines = ["kbd ff 08", "s 30000"]
    for k in range(10):
        lines += ["bp aad8 2000000", "snap %s/walk%d.snap" % (SNAPDIR, k), "s 60000", "bp aad8 2000000"]
    print("walk", run_repl("play_start.snap", lines).count("state saved"))

main()
