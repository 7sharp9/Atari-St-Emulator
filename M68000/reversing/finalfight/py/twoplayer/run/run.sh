#!/bin/sh
# run.sh <tag> <seconds> : play with lua/bot2p.lua. Environment: FF_CH1 FF_CH2 FF_BOT_* (see lua/bot2p.lua), FFD_RUN own MAME run dir.
d=$(cd "$(dirname "$0")/.." && pwd)
. "$d/run/env.sh"
tag=${1:-x}
export FF_BOT_LOG=${FF_BOT_LOG:-$out/$tag.log}
exec sh "$d/run/ffrun.sh" "$d/lua/bot2p.lua" "${2:-300}"
