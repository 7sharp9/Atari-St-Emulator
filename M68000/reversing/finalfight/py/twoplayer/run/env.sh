# env.sh: sourced by every wrapper after it set d (this directory). Output and MAME run directories live under scratchpad/finalfight/twoplayer (gitignored):
#   $base/out       logs, RAM dumps, screenshots      (FFD_OUT overrides)
#   $base/run       MAME cfg, nvram, states, snaps     (FFD_RUN overrides; concurrent runs need their own: run_t, run_1p, ... as run_long.sh does)
root=$(cd "$d/../../../.." && pwd)
base=${FFD_BASE:-$root/scratchpad/finalfight/twoplayer}
out=${FFD_OUT:-$base/out}
runroot=${FFD_RUN:-$base/run}
mkdir -p "$out"
export FFD_OUT=$out
