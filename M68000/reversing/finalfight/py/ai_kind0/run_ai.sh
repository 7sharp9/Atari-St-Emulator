#!/bin/sh
# run_ai.sh <mode> ...   MAME runs for the kind-0 AI checks (headless, SDL dummy). Never starts mame outside this wrapper.
#   rec  <name> <state> <stop> [keys]        poolrec.lua dump -> $AI_OUT/<name>.bin       (FF_GOD=1 tops up Cody, FF_POKE, FF_COPY, FF_WTAP, FF_SHOT_WIN pass through)
#   cold <name> <stop> <lo> <hi> [keys]      cold-boot drive (plans/plan3.lua), dump frames lo..hi
#   hit  <name> <state> <stop> "<addrs>" [keys]   breakpoint execution counts -> $AI_OUT/<name>_hits.txt (FF_LOG=1 also _log.txt with D0/D1/A6/S)
#   poke <name> <idx> <type63> <hp-hex> [facing]  hit-type poke on pool-2 array index <idx> at the end of frame 4200, dump to frame 4420
# Environment: FF_RUN  MAME cfg/nvram/state/snap dir (default $root/scratchpad/finalfight/p3/a/run; give each concurrent run its own)
#              AI_OUT  output dir (default $root/scratchpad/finalfight/p3/a/out)   FF_ROMS ROM path (default ~/mame-roms)
# <state> is a .sta name; it is copied from scratchpad/finalfight/<state>.sta into $FF_RUN/sta/ffightuc/ when missing.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
lua="$root/reversing/finalfight/lua"
run=${FF_RUN:-$root/scratchpad/finalfight/p3/a/run}
out=${AI_OUT:-$root/scratchpad/finalfight/p3/a/out}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap" "$out/tmp"
export SDL_VIDEODRIVER=dummy FF_DIR="$lua" FF_OUT="$out"
mode=$1; shift
need_state() { [ -f "$run/sta/ffightuc/$1.sta" ] || cp "$root/scratchpad/finalfight/$1.sta" "$run/sta/ffightuc/"; }
mame_run() { # $1 = script, rest = extra mame args
  s=$1; shift
  cd "$run" || exit 1
  mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
    -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle "$@" \
    -seconds_to_run 300 -autoboot_script "$s"
}
h() { printf '%x' "$1"; }
case $mode in
  rec)  need_state "$2"
        FF_LOAD=$2 FF_STOP=$3 FF_REC_OUT="$out/$1.bin" FF_KEYS="$4" FF_TAG=$1 FF_WTAP_OUT="$out/$1_wtap.txt" mame_run "$here/poolrec.lua" ;;
  cold) FF_PLAN="$lua/plans/plan3.lua" FF_STOP=$2 FF_REC_LO=$3 FF_REC_HI=$4 FF_REC_OUT="$out/$1.bin" FF_KEYS="$5" FF_TAG=$1 mame_run "$here/poolrec.lua" ;;
  hit)  need_state "$2"; L=""; [ -n "$FF_LOG" ] && L="$out/$1_log.txt"
        FF_HIT_LOG="$L" FF_LOAD=$2 FF_STOP=$3 FF_ADDRS="$4" FF_KEYS="$5" FF_GOD=1 FF_HIT_OUT="$out/$1_hits.txt" FF_TAG=$1 \
          mame_run "$here/hitc.lua" -debug -debugger none ;;
  poke) need_state ff_enemies
        base=$((0xff86e8 + 192 * $2))
        FF_POKE="4200:$(h $((base+63))):1:$3,4200:$(h $((base+62))):1:${5:-1},4200:$(h $((base+24))):2:$4" FF_GOD=1 \
          FF_LOAD=ff_enemies FF_STOP=4420 FF_REC_OUT="$out/$1.bin" FF_KEYS="" FF_TAG=$1 mame_run "$here/poolrec.lua" ;;
  *) echo "usage: $0 rec|cold|hit|poke ..." >&2; exit 2 ;;
esac
