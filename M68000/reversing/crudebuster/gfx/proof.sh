#!/bin/sh
# Re-run every offline gate over the dumps already captured (see README for how the dumps are made).
here=$(cd "$(dirname "$0")" && pwd)
py="$here/../../../.venv/bin/python"
cd "$here" || exit 1
echo "== 1. graphics ROM regions assembled from the zip vs MAME's own"; $py py/gfxlib.py
echo "== 2. renderer vs MAME snapshot, per dump set (frames identical / frames)"
for n in att a1 lv1 lv2 lv3 lv4 lv5; do
  $py py/compare.py dumps/$n run/$n/snap | $py -c "
import sys,collections
rows=[l.split() for l in sys.stdin]
ok=sum(1 for r in rows if r[2]=='61440')
print('$n', ok, '/', len(rows), 'frames 61440/61440 pixels;', 'pri=1 frames', sum(1 for r in rows if r[6]=='pri=1'), ';  band-split frames', sum(1 for r in rows if not r[-1].endswith('=1')))"
done
echo "== 3. sensitivity (rules are exercised)"; $py py/sensitivity.py a1 att lv1 lv2 lv3 lv4 lv5
echo "== 4. palette load model vs live palette RAM"; $py py/palcheck.py
echo "== 5. sprite emitters vs live list entries"; $py py/emitcheck.py dumps/e0 dumps/e3 dumps/e5
echo "== 6. level map model vs live tilemap RAM (layer A, gameplay frames)"
for lv in 1 2 3 4 5; do $py py/levelcheck.py lv$lv $lv A 1800; done; $py py/levelcheck.py a1 0 A 1000
for lv in 3 4; do $py py/levelcheck.py lv$lv $lv C 1800; done; $py py/levelcheck.py a1 0 C 1000
