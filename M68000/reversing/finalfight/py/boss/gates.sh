#!/bin/sh
# gates.sh : the gates over the dumps and logs written by runs.sh ($PAR_OUT, default scratchpad/finalfight/boss/out). Expected counts (boss.md "Evidence"):
#   Cody damage 127 of 127 (e3 11, e4 81, e5 35); boss damage 31 of 32 (the 32nd is the 40-point thrown landing, $3f7a); attack picks 160 of 160;
#   retreat thresholds at hp 165 and 99, angry flag at hp 111 (e3), at 110 after the poke (e5); two-player health 450; ranks 0 and 31 give hp 300, def 1 and 11;
#   s1 counts $390a 1, $5ebc 0, $5f9e 2, $3ed30 0, $38f0 0; s3 shows no write of 6 to +2 of any pool-4 record.
here=$(cd "$(dirname "$0")" && pwd)
root=${M68000_ROOT:-$(cd "$here/../../../.." && pwd)}
O=${PAR_OUT:-$root/scratchpad/finalfight/boss/out}
PY=${PY:-$root/.venv/bin/python}
for r in e3 e4 e5; do echo "== Cody damage $r"; $PY $here/gate_dmg_cody.py $O/$r.bin | sed -n 1,5p; done
echo "== boss damage e3"; $PY $here/gate_dmg_boss.py $O/e3.bin | sed -n 1p
echo "== attack picks"; for r in g1 g2; do $PY $here/gate_pick.py $O/$r.hits $O/$r.bin; done
echo "== thresholds e3"; $PY $here/thresh.py $O/e3.bin
echo "== thresholds e5 (hp poked to 110)"; $PY $here/thresh.py $O/e5.bin
echo "== two players e6"; $PY $here/thresh.py $O/e6.bin | head -1
echo "== ranks 0 and 31"; for r in r0 r31; do $PY $here/rank.py $O/$r.bin; done
echo "== chain roll"; $PY $here/chain.py $O/e3.bin $O/e4.bin $O/e5.bin
echo "== pause release e3 / e8 / e9"; $PY $here/exe.py $O/e3.bin 9130 9145; $PY $here/exe.py $O/e8.bin 9136 9145; $PY $here/exe.py $O/e9.bin 8930 9020 | head -3
echo "== s1 breakpoint counts"; grep COUNT $O/s1.log | tr '\n' ' '; echo
echo "== s2 writers of the boss record in-use byte"; grep ' W ' $O/s2.hits
echo "== s3 writes to +2 of the pool-4 records (count by value written)"; $PY $here/writes.py $O/s3.hits
