#!/bin/sh
# runtime poison of the candidate never-consumed blocks on the remaining screens (options, select track, shop, high-score entry)
cd "$(dirname "$0")/../../../.."  # M68000/
S=scratchpad/supersprint/agents/secrets
R="28e00,37e00,43e00,4be00,53e00"; H="2ce00,38e00,44e00,4ee00,54e00"
python3 $S/py/runtime_poison.py $S/snap/opt.snap 3000000 $R $H 1000 opt > $S/tmp/rp_opt.log 2>&1
python3 $S/py/runtime_poison.py $S/snap/sel2.snap 3000000 $R $H 1000 select > $S/tmp/rp_select.log 2>&1
python3 $S/py/runtime_poison.py $S/snap/shop.snap 3000000 $R $H 1000 shop > $S/tmp/rp_shop.log 2>&1
python3 $S/py/runtime_poison.py $S/snap/pre_hiscore.snap 3000000 $R $H 1000 hiscore "w 1d856 09090909;w 1d85a 09000000;w 1dbfa 00010001" > $S/tmp/rp_hiscore.log 2>&1
