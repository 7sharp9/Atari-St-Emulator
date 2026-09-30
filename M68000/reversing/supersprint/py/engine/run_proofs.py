"""Run every engine proof from a fresh process and print its result lines (no cached corpora: every script pokes state into the snapshot
and calls the real routine through the emulator).  usage: run_proofs.py [quick]    (quick = fewer trials)
Needs: bin/Debug/net8.0/M68000.dll (never rebuilt here), the extracted disk files under scratchpad/supersprint (see reversing/supersprint/py)."""
import os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
quick = len(sys.argv) > 1 and sys.argv[1] == 'quick'
T = (lambda n: str(max(4, n // 5))) if quick else (lambda n: str(n))
JOBS = [
    ('reset-vector picture $10236 (RLE)', ['proof_reset_pic.py']),
    ('tile maps $152d2 + RLE $1484a (full screens)', ['proof_tiles_callcap.py']),
    ('Track-1 background rebuild (tiles+trees+shadows) vs live stash', ['proof_playfield.py']),
    ('car blitter $14a4a', ['proof_cars.py', T(40)]),
    ('tree/shadow $15642, tornado $1404e, explosion $14b8e', ['proof_sprites.py', 'all', T(30)]),
    ('particle $143ca, 16x8 $1416c, tile $14262, helicopter $13cbc, HUD caption $144ca, HUD icon $1453a', ['proof_sprites2.py', 'all', T(30)]),
    ('steering wheel frames $16926/$16962', ['proof_wheel.py']),
    ('glyph blitter $16528', ['proof_text.py', T(40)]),
    ('number formatter $1b522', ['proof_numfmt.py']),
    ('HUD big digits $15e5a', ['proof_hud.py']),
    ('depth layer 0 $154d2', ['proof_layer0.py']),
    ('depth sort $e84c', ['proof_depthsort.py', T(60)]),
    ('dirty rectangles $14972 / $14a4a records', ['proof_dirty.py']),
    ('RNG $a666 (TOS Random)', ['proof_rng.py']),
    ('engine-sound $12450', ['proof_engine_snd.py']),
    ('sound driver model vs real Timer-D ISR (300 ticks x 24 effects)', ['proof_sound.py', '60' if quick else '300']),
]
t0 = time.time()
for title, cmd in JOBS:
    print('=== ' + title, flush=True)
    p = subprocess.run([sys.executable, os.path.join(HERE, cmd[0])] + cmd[1:], capture_output=True, text=True)
    lines = [l for l in p.stdout.split('\n') if l.strip()]
    keep = [l for l in lines if any(k in l for k in ('equal', 'TOTAL', 'pixels', 'mismatch', 'Mismatch', 'MISMATCH', 'consumed', 'path:'))] or lines[-3:]
    print('\n'.join('    ' + l for l in keep[-14:]))
    if p.returncode: print('    !! exit code', p.returncode, p.stderr[-400:])
print('done in %.0f s' % (time.time() - t0))
