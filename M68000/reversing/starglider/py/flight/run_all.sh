#!/bin/bash
# Runs every flight gate; each prints one MATCH line (the broken-model controls must print a lower count).
cd "$(dirname "$0")/../../../.." || exit 1          # the M68000 directory
export ATARI_NOTRACE=1
D=reversing/starglider/py/flight
for g in gate_integrator gate_controls gate_isr; do python3 $D/$g.py 2>&1 | grep -v '^---'; done
python3 $D/gate_integrator.py 100 --broken 2>&1 | grep -v '^---' | head -1
python3 $D/gate_controls.py 100 --broken 2>&1 | grep -v '^---' | head -1
python3 $D/gate_isr.py 30 --broken 2>&1 | grep -v '^---' | head -1
for g in gate_energy gate_laser gate_messages gate_letters gate_definekeys gate_cheat; do python3 $D/$g.py 2>&1 | grep -v '^---'; done
python3 $D/fly.py 2>&1 | grep -v '^---'
