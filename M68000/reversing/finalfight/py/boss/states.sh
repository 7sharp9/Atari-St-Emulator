#!/bin/sh
# states.sh : build the two starting states from a cold boot with py/stage/run.sh (own run directories, nothing shared) and put them in $PAR_SRC/sta/ffightuc:
#   sb_boss  (frame 8298, DAMND not yet initialised; work RAM sha256 a0cb6b52...4837)         = run.sh boss
#   a_area2  (frame 7807, stage 0 area byte 1, camera $900; work RAM sha256 d594bed6...eed4)   = run.sh custom with FF_BOT_CAM=2304
# A state that is already there is kept. About 1 and 2 minutes.
here=$(cd "$(dirname "$0")" && pwd)
root=${M68000_ROOT:-$(cd "$here/../../../.." && pwd)}
PAR_ROOT=${PAR_ROOT:-$root/scratchpad/finalfight/boss}; PAR_SRC=${PAR_SRC:-$PAR_ROOT/run}
S=$PAR_SRC/sta/ffightuc; mkdir -p "$S" "$PAR_ROOT/cold"
ff=$root/reversing/finalfight
if [ ! -f "$S/sb_boss.sta" ]; then
  FFS_RUN=$PAR_ROOT/cold/run_boss FFS_OUT=$PAR_ROOT/cold/out_boss sh "$ff/py/stage/run.sh" boss > "$PAR_ROOT/cold/boss.out" 2>&1
  cp "$PAR_ROOT/cold/run_boss/sta/ffightuc/sb_boss.sta" "$S/"
  shasum -a 256 "$PAR_ROOT/cold/out_boss/sb_boss_ram.bin"
fi
if [ ! -f "$S/a_area2.sta" ]; then
  FFS_RUN=$PAR_ROOT/cold/run_area2 FFS_OUT=$PAR_ROOT/cold/out_area2 FF_PLAN=$ff/lua/plans/plan1.lua FF_BOT_START=2450 FF_BOT_CAM=2304 FF_SAVE=a_area2 \
    FF_BOT_LOG=$PAR_ROOT/cold/area2.log sh "$ff/py/stage/run.sh" custom > "$PAR_ROOT/cold/area2.out" 2>&1
  cp "$PAR_ROOT/cold/run_area2/sta/ffightuc/a_area2.sta" "$S/"
  shasum -a 256 "$PAR_ROOT/cold/out_area2/a_area2_ram.bin"
fi
ls -l "$S"
