# env.sh: sourced by the shell scripts of this directory (needs $here set). Sets $root (M68000/), $out (logs; FFA_OUT), $run (MAME run dir; FFA_RUN), $py (the venv python).
root=${M68000_ROOT:-$(cd "$here/../../../.." && pwd)}
out=${FFA_OUT:-$root/scratchpad/finalfight/objects/out}
run=${FFA_RUN:-$root/scratchpad/finalfight/objects/run}
py=$root/.venv/bin/python
mkdir -p "$out"
export FFA_OUT="$out" FFA_RUN="$run"
