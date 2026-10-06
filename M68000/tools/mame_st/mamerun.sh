#!/bin/sh
# mamerun.sh <outdir> <lua> [extra mame args]: run MAME's `st_uk` (Atari ST, TOS 1.00 UK; tos100uk.bin is CRC-identical to M68000/TOS100UK.IMG) headless under a Lua script.
# env MAMEST_ROMS (rompath holding st_uk.zip; default ~/GitHub/mame/roms), MAMEST_* (script options). Work dir scratchpad/mame_st. See DEVELOPING.md "MAME as a second oracle".
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
O=$1; L=$2; shift 2
D=$root/scratchpad/mame_st
mkdir -p "$O" "$D/cfg" "$D/nvram" "$D/sta" "$D/snap"
export SDL_VIDEODRIVER=dummy MAMEST_OUT=$O
cd "$D" || exit 1
exec mame st_uk -rompath "${MAMEST_ROMS:-$HOME/GitHub/mame/roms}" -cfg_directory "$D/cfg" -nvram_directory "$D/nvram" -state_directory "$D/sta" \
  -snapshot_directory "$D/snap" -video none -sound none -nothrottle -skip_gameinfo -autoboot_script "$L" "$@"
