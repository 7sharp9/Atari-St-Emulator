#!/bin/sh
# make_pre.sh [state-name]: cold-boot drive to frame 1900 (control variant, no enemies) and save it as a MAME state
# (default k6_pre) plus <name>_ram.bin / <name>_gfxram.bin in $K6_RUN_DIR.
dir=$(cd "$(dirname "$0")" && pwd)
n=${1:-k6_pre}
FF_VARIANT=ctl FF_TAG=$n FF_SAVE=$n FF_SAVE_FRAME=1900 "$dir/ffrun_k6.sh" "$dir/../../lua/ffdrive.lua" 120 > /dev/null 2>&1
