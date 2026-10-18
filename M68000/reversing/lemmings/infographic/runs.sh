#!/bin/bash
# Re-run every skilldrive.py run the infographic plates use, into scratchpad/lemmings/info/runs/<name>/.
# Run from M68000/ with sel.snap in place (mechanics.md "Skill assignment"); the runs go in parallel (about a minute).
# Pokes of terrain (--wall, --wallval) are inputs: see each plate's "how" line in template.html.
set -e
O=scratchpad/lemmings/info/runs; mkdir -p $O
SD=reversing/lemmings/py/skilldrive.py
go() { n=$1; idx=$2; cnt=$3; shift 3; python3 $SD $idx $cnt $O/$n "$@" >/dev/null & }
go climb   0 26c22 --samples 80 --step 36000 --x0 688 --y0 40 --rows 56  --wall 46,48,56,74
go float   1 26c2a --samples 70 --step 36000 --x0 688 --y0 56 --rows 100 --wall 47,47,76,139,00000000
go ctl     1 26c2a --samples 70 --step 36000 --x0 688 --y0 56 --rows 100 --wall 47,47,76,139,00000000 --noclick
go bomb    2 26c1e --samples 110 --step 54000 --x0 768 --y0 66 --rows 44
go build   4 26c24 --samples 100 --step 72000 --x0 688 --y0 56 --rows 48  --wall 45,49,70,75,00000000
go bashw   5 26c28 --samples 40 --step 30000 --x0 688 --y0 56 --rows 40  --wall 46,48,56,74
go mine    6 26c2c --samples 100 --step 36000 --x0 688 --y0 56 --rows 56
go dig     7 26c20 --samples 60 --step 36000 --x0 688 --y0 60 --rows 50
wait
reversing/lemmings/py/stepsweep.sh $O/step >/dev/null
