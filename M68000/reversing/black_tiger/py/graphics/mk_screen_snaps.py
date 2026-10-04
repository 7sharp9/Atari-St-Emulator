"""mk_screen_snaps.py - intro, ending and shop snapshots.
 intro  : agents/systems/title_screen.snap, fire, bp $ec02 (BT001 shown), $ec10 (flash), $ec6e (story text), $ec72 (after fade): NATURAL, no pokes.
 ending : LABELLED POKE: boss slot cleared (w 1f020 00000000) on B7_p1.snap (level 7 boss spawned by mk_boss_snaps.py) so
          $c642 sees the boss slot empty on level 7 and enters the ending $c718; bp at $c718/$c752/$c76e/$c794/$c7ba/$c7e0.
 shop   : LABELLED POKE: hero record moved onto the shop man cell (level 0, (1256,224)), bp $f690, 300,000 steps."""
from drive import *

def main():
    d = os.path.join(OUT, "screens"); os.makedirs(d, exist_ok=True)
    L = ["kbd ff 80", "s 100000", "kbd ff 00"]
    for tag, addr in (("intro_pic", "ec02"), ("intro_flash", "ec10"), ("intro_text_before", "ec6e"), ("intro_after_fade", "ec72")):
        L += ["bp %s 100000000" % addr, "snap %s/%s.snap" % (d, tag), "s 1"]
    print("intro", run_repl("agents/systems/title_screen.snap", L).count("state saved"))
    L = ["w 1f020 00000000"]
    for tag, addr in (("end_entry", "c718"), ("end_pic", "c752"), ("end_text1", "c76e"), ("end_text2", "c794"), ("end_text3", "c7ba"), ("end_text4", "c7e0")):
        L += ["bp %s 20000000" % addr, "snap %s/%s.snap" % (d, tag), "s 1"]
    print("ending", run_repl(os.path.join(OUT, "boss", "B7_p1.snap"), L).count("state saved"))
    os.makedirs(os.path.join(OUT, "shop"), exist_ok=True)
    out = run_repl("play_start.snap", ["w 1f014 04e800e0", "bp f690 3000000", "s 300000", "snap %s/shop/shop_a.snap" % OUT])
    print("shop", out.count("state saved"))

main()
