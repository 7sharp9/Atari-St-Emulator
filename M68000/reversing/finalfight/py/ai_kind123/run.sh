#!/bin/sh
# run.sh <tag> <stop> [ENV=VAL ...]: load ff_enemies, run fdrive.lua (or $LUA) to frame <stop>; per-frame records go to $AI123_OUT/<tag>_rec.txt.
#   AI123_RUN  MAME run directory (cfg, nvram, sta, snap); default <repo>/scratchpad/finalfight/p3/b/run. Two runs sharing one directory collide.
#   AI123_OUT  output directory (logs, records, RAM dumps); default <repo>/scratchpad/finalfight/p3/b/out
#   LUA        driver in this directory (fdrive.lua default; hits.lua, pcprobe.lua, crashprobe.lua)
# Needs ~/mame-roms (FF_ROMS overrides) and scratchpad/finalfight/ff_enemies.sta (copied into $AI123_RUN/sta/ffightuc/ when missing).
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
RUN=${AI123_RUN:-$root/scratchpad/finalfight/p3/b/run}
OUT=${AI123_OUT:-$root/scratchpad/finalfight/p3/b/out}
tag=$1; stop=$2; shift 2
mkdir -p "$RUN/cfg" "$RUN/nvram" "$RUN/sta/ffightuc" "$RUN/snap" "$OUT/tmp"
for s in ff_enemies ff_gameplay; do
  [ -f "$RUN/sta/ffightuc/$s.sta" ] || cp "$root/scratchpad/finalfight/$s.sta" "$RUN/sta/ffightuc/" 2>/dev/null
done
export FF_DIR="$root/reversing/finalfight/lua" FF_AI123="$here" FF_OUT="$OUT"
export FF_LOAD=${FF_LOAD:-ff_enemies} FF_STOP=$stop FF_TAG=$tag FF_REC="$OUT/${tag}_rec.txt" FF_REC_LO=${FF_REC_LO:-4151}
for kv in "$@"; do export "$kv"; done
# headless: without the dummy SDL driver macOS makes mame the frontmost app
export SDL_VIDEODRIVER=dummy
cd "$RUN" || exit 1
mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$RUN/cfg" -nvram_directory "$RUN/nvram" \
  -state_directory "$RUN/sta" -snapshot_directory "$RUN/snap" -video none -sound none -nothrottle ${FF_MAMEARGS} \
  -seconds_to_run 300 -autoboot_script "$here/${LUA:-fdrive.lua}" > "$OUT/${tag}.log" 2>&1
tail -n 3 "$OUT/${tag}.log"
