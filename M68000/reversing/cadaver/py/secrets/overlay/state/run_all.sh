#!/bin/sh
# run_all.sh: re-run every proof of the state/anim/mover/door section of secrets.md ("The type-6 record's state bytes", about 6 minutes).
# Outputs go to $OUTDIR (default M68000/scratchpad/cadaver/s91_state).  Needs M68000/.venv and bin/Debug/net8.0/M68000.dll (read-only use).  Snapshots default to the lineage paths in each script;
# override with SNAP_CAVERN, SNAP_URN53, SNAP_ROOM31, SNAP_ROOM90, SNAP_WATER30, SNAP_ROOM29, SNAP_ROOM13, SNAP_WALL12, SNAP_DOOR3B, SNAP_TUNNEL.
HERE="$(cd "$(dirname "$0")" && pwd)"
M68="$(cd "$HERE/../../../../../.." && pwd)"
cd "$M68" || exit 1
PY=.venv/bin/python
D=reversing/cadaver/py/secrets/overlay/state
export OUTDIR="${OUTDIR:-$M68/scratchpad/cadaver/s91_state}"
mkdir -p "$OUTDIR"
SNAPS="scratchpad/cadaver/gameplay_empire.snap scratchpad/cadaver/level1_loaded.snap"
for f in layout_claims room_byte_check flag_corr bit6_corr door_census inst_census f15_census anim_op_census mover_prog_census; do $PY $D/$f.py $SNAPS > $OUTDIR/$f.out 2>&1; done
for s in $SNAPS; do $PY $D/layout_stats.py $s; done > $OUTDIR/layout_stats.out 2>&1
$PY $D/scan_snaps.py $OUTDIR/scan_snaps.tsv; $PY $D/make_batches.py $OUTDIR
$PY $D/e1_anim_trace.py 40 > $OUTDIR/e1_anim_trace.out 2>&1
for x in e2_lever e3_door_matrix e4_l1_lever562 x1_hide x3_lock_collision x4_gravity_bits x5_mover_gates x6_hazard x7_relock x8_examine_bit5 x9_verb_matrix x10_invulnerable x11_anim_gates x12_mover_template_bits x13_event11_fall x14_refusal_slide; do $PY $D/$x.py > $OUTDIR/$x.out 2>&1; done
# free-run gates over sampled snapshots (one per distinct room / object set; snapshots stuck in the $0117c4 assert spin are reported 'PC never reached' and skipped)
(for s in $(cat $OUTDIR/batch_snaps.txt) scratchpad/cadaver/gameplay_empire.snap scratchpad/cadaver/s86/a3/snap/r36_486_operated.snap scratchpad/cadaver/s86/a3/snap/r36_dragon_dead.snap; do echo "== $s"; $PY $D/anim_free_run.py $s 40 2>&1 | tail -12; done) > $OUTDIR/anim_batch.out 2>&1
(for s in $(cat $OUTDIR/batch_mover.txt) scratchpad/cadaver/s86/a7/snaps/gomove31.snap; do echo "== $s"; $PY $D/mover_free_run.py $s 30 2>&1 | tail -8; done) > $OUTDIR/mover_batch.out 2>&1
$PY $D/summarize_batches.py $OUTDIR > $OUTDIR/gates_summary.out
cat $OUTDIR/gates_summary.out
