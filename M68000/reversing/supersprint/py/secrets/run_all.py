"""run_all.py - re-run every quick headline proof of the `secrets` audit from a fresh checkout state (emulator DLL must exist).
Snapshots are rebuilt from the four anchor snapshots.  Long jobs (run separately, ~3-15 min each on 6 cores):
   python3 py/scan_keys.py <snap> <tag> --steps 3000000 --pre 500000          exhaustive scancode scan  (attract: ss_attract.snap, demo: snap/att_demo.snap with --steps 2000000)
   python3 py/bootpoison.py INIT.DAT 256 | SUPER1.DAT 256 | SUPER.DAT 2048   cold-boot poison scans of the three data files
   python3 py/runtime_poison.py SNAP_ATTRACT 27000000 28e00 59700 1000 attract   runtime poison scans of the in-place SUPER.DAT buffer
   python3 py/poison.py snap/boot_2_72M.snap 64336 656b6 15300000             SUPER1.DAT tail never read
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import sscfg
steps = [
    ('static reachability (unreached routines)', ['reach.py']),
    ('dead-block scan inside reachable functions', ['deadblocks.py']),
    ('DATA-segment strings and their users', ['data_strings.py']),
    ('disk audit (FAT12)', ['disk_audit.py']),
    ('build snapshots (options, pre_winner, prep_kbd, race_kbd)', ['build_snaps.py']),
    ('F5 at the winner\'s circle A/B', ['f5_winner.py']),
    ('options screen F2/F3/F4/F9/F10', ['options_test.py']),
    ('in-race F8 pause / F10 abort / other keys', ['race_keys.py']),
    ('keyboard player in a race (LShift/RShift/Alt, A/Z/L, D/X/\')', ['mk_race_kbd.py']),
    ('  ... input matrix on that snapshot', ['race_input.py', os.path.join(sscfg.WORK, 'agents', 'secrets', 'snap', 'race_kbd.snap')]),
    ('ESC on the prepare screen', ['esc_prepare.py']),
    ('who can start a session', ['fire_sources.py']),
    ('mouse packets ghost-press keys', ['mouse_ghost.py']),
    ('high-score initials entry', ['hiscore_entry.py']),
    ('dead keypad counter $e74a', ['dead_counter.py']),
    ('track range of SELECT TRACK', ['track_range.py']),
]
for title, cmd in steps:
    print('=' * 8, title, flush=True)
    subprocess.run([sys.executable, os.path.join(HERE, cmd[0])] + cmd[1:], cwd=HERE)
