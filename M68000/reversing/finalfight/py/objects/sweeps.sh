#!/bin/sh
# sweeps.sh : the area sweeps of the placed pool 8 kinds (area_sweep.sh), no gfx hashing; shots are named <tag>_<rel>.png under run/snap
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
cd "$here" || exit 1
./area_sweep.sh s1a1 01 01 500 d00 900 50 "250,500,750" off
./area_sweep.sh s1a2 01 02 f00 1400 500 50 "150,300,450" off
./area_sweep.sh s2a1 02 01 f00 1500 600 50 "200,400,600" off
./area_sweep.sh s2a2 02 02 730 f00 800 50 "300,500,700" off
./area_sweep.sh s3a0 03 00 10 d00 1000 50 "300,600,900" off
./area_sweep.sh s4a0 04 00 10 1b00 1500 50 "400,800,1200" off
./area_sweep.sh s5a0 05 00 10 1300 900 50 "300,500,700" off
./area_sweep.sh s5a2 05 02 2700 33c0 700 50 "300,500,700" off
echo done > out/sweeps.done
