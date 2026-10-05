#!/bin/sh
# k3run.sh <tag> <spawn> <stop> <plan> : ff_enemies + FF_SPAWN, breakpoint hit logs on the $1b428 call sites (hits.lua of py/ai_kind123); out/k3/<tag>_hits.txt, _hitlog.txt
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../../.." && pwd); K=$root/reversing/finalfight/py/ai_kind123
base=${FFB_BASE:-$(cd "$here/../../../.." && pwd)/scratchpad/finalfight/engine}   # work area (runs/, out/, run/sta/); default scratchpad/finalfight/engine; FFB_BASE overrides
tag=$1; spawn=$2; stop=$3; plan=$4
ADDRS=${ADDRS:-"1b428,2d0c2,2d178,2d352,2de58,2ed96,315e0,3ed0e,426d8,477bc,4d550"}
mkdir -p $base/out/k3
AI123_RUN=$base/runs/run_$tag AI123_OUT=$base/out/k3 LUA=hits.lua FF_MAMEARGS="-debug -debugger none" sh $K/run.sh $tag $stop FF_SPAWN="$spawn" FF_NOSCRIPT=1 FF_KILL=4152 FF_KEEPHP=1 FF_PLAN=$plan FF_ADDRS="$ADDRS" FF_HIT_OUT=$base/out/k3/${tag}_hits.txt FF_HIT_LOG=$base/out/k3/${tag}_hitlog.txt > /dev/null 2>&1
