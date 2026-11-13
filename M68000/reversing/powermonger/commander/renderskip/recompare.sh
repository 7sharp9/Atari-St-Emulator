#!/bin/bash
# recompare.sh <ladder_dir> <snapnames...>: re-run compare.py over a finished ladder's dumps (after a compare.py change).
set -u
d=$(cd "$(dirname "$0")" && pwd); O=$1; shift
: > "$O/compare.jsonl"
for n in "$@"; do
  for f in "$O/$n"/*_k*.ram; do
    b=$(basename "$f" .ram); tag=${b%_k*}; k=${b##*_k}
    [ "$tag" = base_a ] && continue
    ign=""; [ "$tag" = divider ] && ign="--ignore 57fee:4"
    printf '{"snap":"%s","tag":"%s","k":%s,"cmp":' "$n" "$tag" "$k" >> "$O/compare.jsonl"
    python3 "$d/compare.py" "$O/$n/base_a_k$k.ram" "$f" --json $ign | tr -d '\n' >> "$O/compare.jsonl"
    echo '}' >> "$O/compare.jsonl"
  done
done
