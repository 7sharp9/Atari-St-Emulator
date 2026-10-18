#!/bin/bash
# Walker step/hop/wall thresholds: flatten the ground in front of lemming 0 (sel.snap, level 1), put a solid step of
# H rows (H = 0..8) at x = 752 and print lemming 0's (x, y, dir, state) per tick (36,000 steps). Run from M68000/:
#   reversing/lemmings/py/stepsweep.sh <out dir>
# Ground row is 80 after the flatten (rows 50..79 cleared), the step fills rows 80-H..79 of group 47.
out=${1:?out dir}; mkdir -p "$out"
for h in 0 1 2 3 4 5 6 7 8; do
  args=(--noclick --samples 34 --step 36000 --rows 24 --y0 62 --wall 45,52,50,79,00000000)
  [ $h -gt 0 ] && args+=(--wall 47,47,$((80-h)),79,ffffffff)
  python3 "$(dirname "$0")/skilldrive.py" 0 26c22 "$out/h$h" "${args[@]}" >/dev/null &
done
wait
python3 - "$out" <<'PY'
import re, sys
for h in range(9):
    last, o = None, []
    for l in open('%s/h%d/frames.txt' % (sys.argv[1], h)):
        m = re.match(r'== (\S+) lemming0 x=(\d+) y=(\d+) dir=(-?\d+) state=(\w+)', l)
        if m and m.group(1) != 'pre-click':
            k = m.group(3, 4, 5)
            if k != last: o.append('x%s y%s d%s s%s' % ((m.group(2),) + k)); last = k
    print('H=%d: %s' % (h, ' | '.join(o)))
PY
