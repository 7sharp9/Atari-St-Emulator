#!/bin/sh
# run_pvp.sh : the player-versus-player and two-player runs (each 3 to 10 s from the two-player states made by run/make_states.sh), logs $FFD_OUT/pv_*.txt
here=$(cd "$(dirname "$0")" && pwd); d=$(cd "$here/../.." && pwd)
. "$d/run/env.sh"
P="sh $d/run/prun.sh"; S=d2p_ch12_1900
$P pv_c1 $S c1 320 FF_POKES=$d/lua/pokes_adj.lua                                   # P1 (Cody) jabs P2 (Haggar) 40 px away: +148 immunity
$P pv_c1_clr $S c1 320 FF_POKES=$d/lua/pokes_adj.lua FF_CLR148=1                   # same with the victim's +148 cleared every frame: every swing that overlaps hits
$P pv_jump1 $S jump1 400 FF_POKES=$d/lua/pokes_adj.lua FF_CLR148=1 FF_DX=30        # P1 jump attack, special, jump kick
$P pv_p2c1 $S p2c1 320 FF_POKES=$d/lua/pokes_adj.lua                               # P2 jabs P1
$P pv_kill $S c1b 600 FF_POKES=$d/lua/pokes_adj_lowhp.lua FF_CLR148=1              # P2 at hp 0: one jab kills
$P pv_keys $S p2keys 240                                                           # P2's seven inputs through 94(A5)
for dy in -16 -14 -13 -12 -11 -9 -5 0 5 8 9 10 11 13 16; do $P pv_dy_$dy $S jab1 40 FF_POKES=$d/lua/pokes_adj_dy.lua FF_DY=$dy; done
for dy in -11 -10 -9 11 12 13 14; do $P pv_dyb_$dy $S jab1 40 FF_POKES=$d/lua/pokes_adj_dy2.lua FF_DY=$dy; done
$P pv_c1_shot $S c1 60 FF_POKES=$d/lua/pokes_adj.lua FF_SHOTS=16,24 FF_TAG=c1; $P pv_p2_shot $S p2c1 60 FF_POKES=$d/lua/pokes_adj.lua FF_SHOTS=22 FF_TAG=p2   # HUD enemy bars ($runroot/snap/pvp_*.png)
$P pv_kill_p2 d2pw_ch12_1930 p2c1long 330 FF_KILL=0 FF_POKES=$d/lua/pokes_bred_p2b.lua FF_EXTRA=$d/lua/extra_enemy.lua   # P2 kills Bred: the award goes to P2
