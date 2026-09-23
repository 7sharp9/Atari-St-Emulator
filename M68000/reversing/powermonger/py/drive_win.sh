#!/usr/bin/env bash
# run from M68000/; output in $PM_WORK/win (default scratchpad/pmwork/win)
# drive_win.sh: mission 1 (campaign land 0) won with real clicks, then the campaign step to land 1.
#   briefing OK (pokes, as build_land.sh) -> settle 30M -> sword icon (arms order $0c) -> minimap click
#   on the enemy lord 0's cell (22,45) -> 50M steps (fight, $550e defection, ratio 4) -> options icon
#   -> GAME -> RETIRE (order $2e -> $d2c8 victory, $3f2a0[0] := 1) -> Continue Conquest -> land 1.
d=${PM_WORK:-scratchpad/pmwork}/win; mkdir -p $d
P=reversing/powermonger/py
python3 $P/clicks.py w:2df92:001400b1 w:2df8e:001400b1 w:2df96:00010001 u:13ce6:80000000 \
  s:30000000 u:f898:5000000 snap:$d/m1_s0.snap \
  home 243,190 m:57fd4:2 22,51 snap:$d/m1_atk.snap \
  s:50000000 u:f898:5000000 snap:$d/m1_ready.snap m:57fce:2 \
  home 71,138 47,26 watch:3f2a0:1 30,14 s:40000000 unwatch snap:$d/m1_win.snap m:3f2a0:1 \
  home 160,102 bp:1120e:30000000 s:20000000 snap:$d/m1_map.snap \
  home 40,20 bp:11414:5000000 m:580a4:2 u:f898:80000000 s:30000000 u:f898:5000000 snap:$d/l1_built.snap q > $d/win.cmds
start=$(date +%s)
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm67_ok_pre.snap repl --disk-a scratchpad/powermonger.st < $d/win.cmds > $d/win.txt 2>&1
echo "$(( $(date +%s)-start ))s"; grep -E 'WATCH|breakpoint|saved' $d/win.txt
python3 $P/snap2ram.py $d/m1_ready.snap && python3 $P/sides.py $d/m1_ready.ram | head -5
