#!/bin/sh
# run.sh trans|pt <name>: run lua/trans.lua (transition log) or lua/pctap.lua (PC-tagged write taps) on top of lua/stagebot.lua (the bot that plays player 1).
# Own MAME run directory ($FFT_RUN, default <repo>/scratchpad/finalfight/transitions/run) and output directory ($FFT_OUT, default .../out): two runs never share cfg, nvram, states.
# Logs: $FFT_OUT/<name>.log (trans) or <name>.pt (pt), the bot's own log <name>.bot. States saved with FF_SAVE go to $FFT_RUN/sta/ffightuc/.
# Environment, everything stagebot.lua takes (FF_LOAD, FF_PLAN, FF_BOT_START, FF_BOT_STOPF, FF_BOT_CAM, FF_BOT_GOD, FF_SAVE ...) plus
#   trans: FF_TR_POKE="f:hexaddr:hexbytes,..." (pokes at frame end), FF_TR_HOLD="f1-f2:field:level,..." (inputs applied after the bot), FF_TR_TAPS=0, FF_TR_POOLS=0
#   pt:    FF_PT_W="lo-hi,..." / FF_PT_R write / read taps (word-aligned inclusive ranges: lo even, hi odd), FF_PT_LO, FF_PT_HI frame window
#   FF_STOP=<frame> ends a run in which the bot is off (FF_BOT_START=99999); FFT_SECONDS (default 900)
here=$(cd "$(dirname "$0")" && pwd)
root=${M68000_ROOT:-$here}
while [ ! -f "$root/reversing/finalfight/lua/stagebot.lua" ] && [ "$root" != "/" ]; do root=$(dirname "$root"); done
ff=$root/reversing/finalfight
run=${FFT_RUN:-$root/scratchpad/finalfight/transitions/run}
out=${FFT_OUT:-$root/scratchpad/finalfight/transitions/out}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap" "$out/tmp"
export FF_DIR="$ff/lua" FF_OUT="$out" SDL_VIDEODRIVER=dummy
export FF_SAVE_FRAME=99999 FF_STOP=${FF_STOP:-60000}
kind=$1; name=$2
case "$kind" in
  trans) script=$here/trans.lua; export FF_TR_LOG="$out/$name.log" ;;
  pt)    script=$here/pctap.lua; export FF_PT_OUT="$out/$name.pt" ;;
  *) echo "usage: $0 trans|pt <name>" >&2; exit 2 ;;
esac
export FF_BOT_LOG="$out/$name.bot"
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle ${FF_MAMEARGS} \
  -seconds_to_run "${FFT_SECONDS:-900}" -autoboot_script "$script"
