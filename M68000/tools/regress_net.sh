#!/bin/bash
# Regression net (reverse-engineer-st-game skill, section 6) as an A/B of two built DLLs, for the Mac
# (no run.ps1) and for when another session holds bin/: build each side with
#   dotnet build -c Debug M68000.fsproj -o <dir>
# and pass the two M68000.dll paths. Runs from M68000/ (the ROM path is cwd-relative).
#
#   bash tools/regress_net.sh <base.dll> <new.dll> <outdir>
#
# Per build: verify 5000000; a 30M-step diskless snapshot; with CADAVER_SNAP and CADAVER_ST set, a
# 2M-step game resume with a REPL watch on $189ca-$189cd for the first 300,000 (the MMU fast-path
# compare selftest cannot give), and a 4M-step cold boot from that disk watching $0-$7ffff for
# DMA sector lines. Then cmp/diff base against new and selftest the new build. A pass is: both
# VERIFY PASS, every compare IDENTICAL, selftest 0 wrong and 9 skip.
set -u
[ $# -eq 3 ] || { echo "usage: $0 <base.dll> <new.dll> <outdir>" >&2; exit 2; }
BASE=$1; NEW=$2; R=$3
d=$(cd "$(dirname "$0")" && pwd)
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); [ "$d" = / ] && { echo "no repo root" >&2; exit 2; }; done
cd "$d"
mkdir -p "$R"
export ATARI_NOTRACE=1
for v in base new; do
  if [ $v = base ]; then D=$BASE; else D=$NEW; fi
  echo "== $v verify"; dotnet exec "$D" 5000000 verify 2>&1 | tail -1
  dotnet exec "$D" 30000000 snapshot "$R/$v.30m.snap" >/dev/null 2>&1
  if [ -n "${CADAVER_SNAP:-}" ] && [ -n "${CADAVER_ST:-}" ]; then
    printf 'watch 189ca 4\ns 300000\nunwatch\ns 1700000\nsnap %s\nq\n' "$R/$v.cad.snap" \
      | dotnet exec "$D" resume "$CADAVER_SNAP" repl --disk-a "$CADAVER_ST" >/dev/null 2>"$R/$v.cad.err"
    echo "== $v game watch lines: $(grep -c '^WATCH' "$R/$v.cad.err")"
    printf 'watch 0 80000\ns 4000000\nq\n' | dotnet exec "$D" 1 repl --disk-a "$CADAVER_ST" 2>&1 >/dev/null \
      | grep 'DMA' > "$R/$v.dma.txt"
    echo "== $v DMA watch lines: $(wc -l < "$R/$v.dma.txt")"
  fi
done
echo "== compare"
cmp "$R/base.30m.snap" "$R/new.30m.snap" && echo "30M IDENTICAL"
if [ -n "${CADAVER_SNAP:-}" ] && [ -n "${CADAVER_ST:-}" ]; then
  cmp "$R/base.cad.snap" "$R/new.cad.snap" && echo "GAME SNAPSHOT IDENTICAL"
  diff <(grep '^WATCH' "$R/base.cad.err") <(grep '^WATCH' "$R/new.cad.err") && echo "GAME WATCH IDENTICAL"
  diff "$R/base.dma.txt" "$R/new.dma.txt" && echo "DMA WATCH IDENTICAL"
fi
echo "== selftest new"; dotnet exec "$NEW" selftest tests/680x0 2>&1 | tail -3
