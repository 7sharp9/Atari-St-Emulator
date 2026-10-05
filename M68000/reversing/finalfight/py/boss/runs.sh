#!/bin/sh
# runs.sh : regenerate every run behind the claims in boss.md, from sb_boss and a_area2 (states.sh builds them into $PAR_SRC/sta/ffightuc if missing).
# Each run takes 1 to 3 minutes; they are independent, so they are started together (own run directories, own outputs under $PAR_OUT).
# Output default: scratchpad/finalfight/boss/out (dumps of 40 to 65 MB each). Then run gates.sh.
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/states.sh" || exit 1
root=${M68000_ROOT:-$(cd "$here/../../../.." && pwd)}
O=${PAR_OUT:-$root/scratchpad/finalfight/boss/out}; mkdir -p "$O"; export PAR_OUT=$O
P="sh $here/par.sh"
$P e3 DM_LOAD=sb_boss DM_BOT=1 DM_STOPF=11800 DM_LOGN=5 DM_DUMP=$O/e3.bin &                     # bot plays the fight to the stage change
$P e4 DM_LOAD=sb_boss DM_BOT=0 DM_STOPF=13300 DM_DUMP=$O/e4.bin &                               # Cody idle next to the boss: attack picks, damage on Cody
$P e5 DM_LOAD=sb_boss DM_BOT=0 DM_STOPF=11300 DM_DUMP=$O/e5.bin DM_POKES=8310:ff9a80:006e &      # boss hp poked to 110: angry flag, first retreat
$P e6 DM_LOAD=sb_boss DM_BOT=0 DM_STOPF=8900 DM_DUMP=$O/e6.bin DM_POKES=8299:ffd46a:03 &         # 21610(A5) = 3 before the init: two-player health 450
$P e8 DM_LOAD=sb_boss DM_BOT=1 DM_STOPF=10500 DM_DUMP=$O/e8.bin DM_POKES=9138:ffb1fe:00 &        # pause flag cleared before the release: $5f9e restart branch
$P e9 DM_LOAD=sb_boss DM_BOT=1 DM_STOPF=12700 DM_DUMP=$O/e9.bin DM_POKES=8310:ff9a80:0014 &      # boss killed before the second retreat: pause stays
$P g1 DM_DEBUG=1 DM_LOAD=sb_boss DM_BOT=0 DM_STOPF=13300 DM_ADDRS=3dbbc,3dbc0,406f2,3dbb2,3db9c,3d6a0 DM_HITLOG=$O/g1.hits DM_DUMP=$O/g1.bin &
$P g2 DM_DEBUG=1 DM_LOAD=sb_boss DM_BOT=0 DM_STOPF=11300 DM_POKES=8310:ff9a80:006e DM_ADDRS=3dbbc,3dbc0,406f2,3dbb2,3db9c DM_HITLOG=$O/g2.hits DM_DUMP=$O/g2.bin &
$P e7 DM_DEBUG=1 DM_LOAD=sb_boss DM_BOT=0 DM_STOPF=10300 DM_KEYS=left:8300-10300 DM_POKES=8330:ff9a6e:0bf0 DM_ADDRS=3d694,3d6a0,3d732,3d74c,3d760,3d81e,3d8f2,3d912,3d9aa,3da9a,3db98,3edbe,3e460 DM_HITLOG=$O/e7.hits DM_DUMP=$O/e7.bin &
$P s1 DM_DEBUG=1 DM_LOAD=a_area2 DM_BOT=1 DM_STOPF=12200 DM_ADDRS=390a,605c,607a,6278,61a8,3d3fe,3d42a,5f9e,3e8ae,3ed30,3ecea,288c,38f0,5ebc,3946 DM_HITLOG=$O/s1.hits DM_DUMP=$O/s1.bin &
$P s2 DM_DEBUG=1 DM_LOAD=a_area2 DM_BOT=1 DM_STOPF=11700 DM_WPS=ff9a68:1 DM_HITLOG=$O/s2.hits &   # writers of the boss record's in-use byte: $61fe (spawn) and $9b0a (pool clear, stage change)
$P s3 DM_DEBUG=1 DM_LOAD=a_area2 DM_BOT=1 DM_STOPF=11700 DM_WPS=ff952a:1,ff95ea:1,ff96aa:1,ff976a:1,ff982a:1,ff98ea:1,ff99aa:1,ff9a6a:1 DM_HITLOG=$O/s3.hits &   # write taps on +2 of all eight pool-4 records
$P d1 DM_LOAD=sb_boss DM_BOT=1 DM_STOPF=9000 DM_SAVE=a_boss_mid DM_SAVEHP=200 DM_SHOT=8330,8450,8850 DM_SHOTNAME=d1 &
$P r0 DM_LOAD=sb_boss DM_BOT=0 DM_STOPF=8330 DM_DUMP=$O/r0.bin DM_POKES=8299:ff80a8:0000 &      # rank 0 before the init
$P r31 DM_LOAD=sb_boss DM_BOT=0 DM_STOPF=8330 DM_DUMP=$O/r31.bin DM_POKES=8299:ff80a8:001f &    # rank 31 before the init
wait
