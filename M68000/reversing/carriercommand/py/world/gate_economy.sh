#!/bin/bash
# Gate for the economy rules (economy.md section 4) and the RNG (section 2).
# Runs 60M steps from c_s30.snap with a watch on the 64 econ records ($66ec0, 64 x 50 bytes), then replays
# the log through prove_production.py, prove_line.py and prove_transfer.py. `reuse` skips the run.
set -e
here=$(cd "$(dirname "$0")" && pwd)
root=$here; while [ ! -f "$root/tools/rdis.py" ]; do root=$(dirname "$root"); done
work=${CARRIER_WORK:-$root/scratchpad/carrier}
out=$work/world; mkdir -p "$out"
cd "$root"
if [ "$1" != reuse ]; then
  rm -f "$out/w60_err.txt"
  printf 'watch 66ec0 3200\ns 60000000\n' | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll \
    resume "$work/c_s30.snap" repl > /dev/null 2> "$out/w60_err.txt"
fi
echo "watch lines: $(grep -c WATCH "$out/w60_err.txt")"
uv run python -I "$here/prove_production.py" "$out/w60_err.txt" | head -1 \
  | awk '{print; printf "production %d/%d\n", $5, $5+$7}'
uv run python -I "$here/prove_line.py" "$out/w60_err.txt" | tail -1 \
  | awk '{print; printf "line cost %d/%d, step decrement %d/%d\n", $5, $5+$7, $12, $12+$14}'
lt=$(uv run python -I "$here/prove_transfer.py" "$out/w60_err.txt")
echo "packet landings $(grep -c ' MATCH' <<< "$lt")/$(grep -c '^landing' <<< "$lt")"
# RNG: one call of $192bc from a known state against rng.py
got=$(printf 'w 1230 01234567\nw 1234 89abcdef\ncallcap 192bc 100\n' | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll \
  resume "$work/c_s30.snap" repl 2>&1 | sed -n 's/^regdelta D0 \$[0-9a-f]*->\$\([0-9a-f]*\).*/\1/p')
want=$(uv run python -I "$here/rng.py" | awk '{print $1}' | sed 's/0x//')
echo "rng: emulator D0=$got model=$want $([ "$got" = "$want" ] && echo 'rng 1/1' || echo 'rng 0/1')"
