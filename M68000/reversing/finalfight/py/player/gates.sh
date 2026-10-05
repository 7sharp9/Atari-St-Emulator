#!/bin/sh
# gates.sh: regenerate every log gates.py reads (about 5 minutes), then run gates.py.
# Environment: FFP_OUT (log directory), FFP_RUN (MAME run directory, must be private to this run); both default under scratchpad/finalfight/p3/f/.
here=$(cd "$(dirname "$0")" && pwd); cd "$here"
root=$(cd "$here/../../../.." && pwd)
export FFP_OUT=${FFP_OUT:-$root/scratchpad/finalfight/p3/f/out}; export FFP_RUN=${FFP_RUN:-$root/scratchpad/finalfight/p3/f/run}
mkdir -p "$FFP_OUT" "$FFP_RUN/sta/ffightuc"; rm -f "$FFP_OUT"/item_*
[ -f "$FFP_RUN/sta/ffightuc/ff_enemies.sta" ] || cp "$root/scratchpad/finalfight/ff_enemies.sta" "$FFP_RUN/sta/ffightuc/"
R=./run.sh
$R c1 c1 120 > /dev/null                                                   # combo chain on Dug (record 11, hp poked to $300)
FF_GOD=1 FF_EXTRA=$here/extra_dummy.lua FF_DX=24 $R j1 j1 650 >/dev/null     # jump attacks, dummy next to Cody, Cody not hittable (+97 = $ff each frame)
FF_GOD=1 FF_EXTRA=$here/extra_dummy.lua FF_DX=24 $R j2 j2 560 >/dev/null
for dx in 30 -30; do FF_GOD=1 FF_EXTRA=$here/extra_dummy.lua FF_DX=$dx $R s1_$dx s1 330 >/dev/null; done
FF_KILL=1 FF_KEEP=99 FF_HEAL=0 FF_POKES=$here/pokes_hp.lua $R s1_none s1 130 >/dev/null   # special with no enemy and no prop in reach
for k in 0x24 0x25 0x26; do FF_KILL=1 FF_KEEP=11 FF_DX=50 FF_GOD=1 FF_POKES=$here/pokes_prop_w.lua FF_EXTRA=$here/extra_fd.lua FF_DROP=$k $R w2_${k}_50 w2 520 >/dev/null; done
for v in a b c d e; do FF_GOD=1 $R g2$v g2$v 260 >/dev/null; done
FF_GOD=1 FF_EXTRA=$here/extra_dummy.lua FF_DX=24 $R bg1 bg1 140 >/dev/null
DRV=pbp.lua FF_BPS=$here/bps/award.lua FF_BP_OUT=$FFP_OUT/award_bp.txt FF_MAMEARGS='-debug -debugger none' FF_KILL=0 FF_HEAL=20 FF_POKES=$here/pokes_grab.lua $R fight1 fight1 700 >/dev/null   # all five enemies, award breakpoints
for hp in 3c 0a 50 52; do FF_GOD=1 FF_EHP=00$hp $R thr_$hp g2a 200 >/dev/null; done      # enemy hp poked before the back throw
for d in 0x00 0x02 0x03 0x07 0x08 0x0c 0x0d 0x13 0x14 0x16 0x1b 0x1f; do for h in 0x20 0x90; do ./itemrun.sh $d $h >/dev/null; done; done
FF_KILL=1 FF_KEEP=99 FF_HEAL=0 FF_POKES=$here/pokes_die2.lua $R die3 none 330 >/dev/null
FF_KILL=1 FF_KEEP=99 FF_HEAL=0 FF_GOD=1 FF_POKES=$here/pokes_life.lua FF_EXTRA=$here/extra_follow.lua $R life1 w3 120 >/dev/null
FF_KILL=0 FF_HEAL=0 FF_EXTRA=$here/extra_enemy.lua FF_POKES=$here/pokes_grab.lua FF_PLAN=$here/plans/rand1.lua FF_SEED=12345 $R rand1b rand1 3000 FF_N=3000 >/dev/null
FF_KILL=1 FF_KEEP=99 FF_HEAL=0 FF_POKES=$here/pokes_walk.lua $R walk1 walk1 620 >/dev/null
for r in 42 43 44 45 46; do FF_KILL=1 FF_KEEP=99 FF_HEAL=0 FF_GOD=1 FF_POKES=$here/pokes_life.lua FF_EXTRA=$here/extra_follow.lua FF_DROP=0x03 $R dr$r dr$r 70 >/dev/null; done
python3 "$here/gates.py" combo jump special weapon items grapple thrown kills walk drop death hist life
