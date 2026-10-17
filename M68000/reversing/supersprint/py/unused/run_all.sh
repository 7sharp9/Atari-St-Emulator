#!/bin/sh
# run_all.sh: reproduce the headline proofs of the `unused` area (run from anywhere; derives M68000/ from this file's location).
# Writes snapshots/data under scratchpad/supersprint/agents/unused/. Needs the work dir (scratchpad/supersprint: files/, Super Sprint.ST, ss_attract.snap, ss_prep.snap, pre_winner.snap in agents/secrets/snap).
# Total about 25 min on an idle machine (the scans poison 28 x 1 KB blocks, three emulators at a time).
cd "$(dirname "$0")/../../../.." || exit 1           # M68000/
PY=.venv/bin/python; U=reversing/supersprint/py/unused
$PY $U/drive_pre.py 0 1 2 3 4 5 6 7                       # snap/pre_T.snap: entry of $be40 (before the track maps are rendered)
for t in 0 1 2 3 4 5 6 7; do $PY $U/scan.py race_start_t$t pre_$t.snap 's 3000000;!dump'; done       # tracks 5..8 consume +0xf000/+0x1b000
$PY $U/scan.py attract_to_select ss_attract.snap 'kbd fe 80;s 400000;kbd fe 00;s 700000;s 1500000;!dump'   # SELECT TRACK entry consumes +0x3000
for k in 2 3; do $PY $U/scan.py winner_anim$k pre_winner.snap "!bpc 1ad80 60000000;!pokew A6-2 $k;s 6000000;!dump"; done
$PY $U/census_b9.py 0 1 2 3                                # every prize frame drawn per animation (census of $1617a)
for p in mid left_top left_bot right_top right_bot top_mid bot_mid left_mid right_mid; do $PY $U/census_heli.py $p; done
SCAN_PROCS=2 $PY $U/heli_flows.py left_top left_bot left_mid right_mid
$PY $U/render_super1.py; $PY $U/render_unused.py; $PY $U/tile_usage.py; python3 $U/overlap.py
