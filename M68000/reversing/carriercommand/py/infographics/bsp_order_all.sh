#!/bin/bash
# The drawing-order check for bsp.facts.md: bsp_order.py over the Manta snapshots, c_s30, c60, c80 and c_mv (2.4M steps each), then
# m_deck with the Manta's angle words $5df5e/$5df60 poked to 8 x 3 values (600k steps each), then the totals.
# Run from anywhere; outputs in WORK/infographics/bsp/.
set -e
here=$(cd "$(dirname "$0")" && pwd)
root=$here; while [ ! -f "$root/tools/rdis.py" ]; do root=$(dirname "$root"); done
cd "$root"
D=scratchpad/carrier/infographics/bsp; mkdir -p $D; rm -f $D/order_*.json
for sn in manta/m_takeoff manta/m_deck manta/m_air c_s30 c60 c80 c_mv; do
  n=$(basename $sn)
  uv run python -I "$here/bsp_order.py" scratchpad/carrier/$sn.snap 2400000 $D/order_$n.json 2>&1 | grep -v -E 'WARNING|^---' > $D/order_$n.txt
done
for yaw in 0000 2000 4000 6000 8000 a000 c000 e000; do for pit in 03e8 2000 e000; do
  uv run python -I "$here/bsp_order.py" scratchpad/carrier/manta/m_deck.snap 600000 $D/order_deck_${yaw}_${pit}.json \
    poke=5df5e:2:$yaw poke=5df60:2:$pit 2>&1 | grep -v -E 'WARNING|^---' > $D/order_deck_${yaw}_${pit}.txt
done; done
uv run python -I "$here/bsp_order_sum.py" $D
