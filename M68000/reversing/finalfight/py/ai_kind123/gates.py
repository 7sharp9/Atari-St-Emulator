"""gates.py [name ...]: fresh-run gates for ai.md "Kinds 1, 2 and 3" (kinds 1-3 of pool 2, spawned into the ff_enemies state by fdrive.lua).
Gates: names, damage, slots, target, guard, determinism (default: all). Every gate launches its own MAME runs through run.sh and reads only
the records those runs write (no reuse of old logs: outputs go to $AI123_OUT, default <repo>/scratchpad/finalfight/p3/b/gate_out, and are wiped per gate file).
Environment: AI123_RUN (MAME run directory, default .../p3/b/gate_run), AI123_OUT, FF_ROMS.  Needs scratchpad/finalfight/ff_main.bin and ff_enemies.sta.
Prints one line per check "GATE <name>: <passed>/<total> ..." and a final PASS/FAIL summary; exit status 1 on a failed gate."""
import os, sys, subprocess, collections, hashlib
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, '../../../..'))
sys.path.insert(0, here)
os.environ.setdefault('AI123_RUN', os.path.join(root, 'scratchpad/finalfight/p3/b/gate_run'))
os.environ.setdefault('AI123_OUT', os.path.join(root, 'scratchpad/finalfight/p3/b/gate_out'))
OUT = os.environ['AI123_OUT']
from anim import rom, rw
from recs import load, w, s16
RUN = os.path.join(here, 'run.sh')
PLANS = os.path.join(here, 'plans')
CLEAN = ['FF_KILL=4151', 'FF_NOSCRIPT=1', 'FF_KEEPHP=1']
results = []

def run(tag, stop, *env, lua=None, debug=False):
    e = dict(os.environ)
    if lua: e['LUA'] = lua
    if debug: e['FF_MAMEARGS'] = '-debug -debugger none'
    for p in ('%s_rec.txt' % tag, '%s_log.txt' % tag, '%s.txt' % tag):
        try: os.remove(os.path.join(OUT, p))
        except OSError: pass
    subprocess.run([RUN, tag, str(stop)] + list(env), env=e, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return os.path.join(OUT, '%s_rec.txt' % tag)

def report(name, ok, total, note=''):
    results.append((name, ok, total))
    print('GATE %s: %d/%d %s' % (name, ok, total, note), flush=True)

def entry_text(addr):  # name text of a $5b640 entry: 10 name tiles after palette, 4 portrait tiles, palette
    t = ''.join(chr(rw(addr + 12 + 2 * i) & 0xff) if rw(addr + 12 + 2 * i) >> 8 == 0x44 else '?' for i in range(10))
    return t.strip()

def name_entry(kind, sub):  # the entry address $5b640 computes for tag 2
    a0 = 0x5b682 + rw(0x5b682 + 2)
    return a0 + rw(a0 + 2 * kind) + 32 * sub

# --- names: HUD enemy-name object, entry pointer and its text, 9 fighters ------------------------------------------------------------
def gate_names():
    cases = [(1, 0, 0, 'J'), (1, 1, 0, 'TWO.P'), (2, 0, 0, 'AXL'), (2, 1, 0, 'SLASH'), (3, 0, 0, 'ANDORE Jr.'), (3, 1, 0, 'ANDORE'),
             (3, 2, 8, 'G.ANDORE'), (3, 3, 8, 'U.ANDORE'), (3, 4, 8, 'F.ANDORE')]
    ok = 0
    for k, s, b21, want in cases:
        rec = run('names_%d_%d' % (k, s), 5200, *CLEAN, 'FF_KEEPEHP=1', 'FF_RECHUD=1', 'FF_SPAWN=4152:%d:%d:%d:128:0:4' % (k, s, b21),
                  'FF_PLAN=' + os.path.join(PLANS, 'tap25.lua'))
        G, P = load(rec)
        got = None
        for f in sorted(P):
            h = P[f].get('hud')
            if h and h[18] == 2 and h[19] == k and h[20] == s:
                got = int.from_bytes(h[148:152], 'big'); break
        good = got == name_entry(k, s) and entry_text(got) == want
        ok += good
        print('   kind %d sub %d: HUD entry %s text %r (expected %r)' % (k, s, hex(got) if got else None, entry_text(got) if got else None, want), flush=True)
    report('names', ok, len(cases))

# --- damage on Cody: attack id -> $2fa2 damage row byte at rank 4 -----------------------------------------------------------------------
CASES = {  # tag: (kind, sub, box base 56(A6), char data base 92(A6) before $2fa2)
    'j0': (1, 0, 0x298c4, 0x29974), 'j1': (1, 1, 0x2a1c0, 0x2a270), 'a0': (2, 0, 0x2be98, 0x2bf30), 'a1': (2, 1, 0x2cb74, 0x2cc0c)}
def expected_damage(a0, cd, atk, rank=4):
    e = a0 + rw(a0) + 16 * atk
    return rom[cd + 0x60 + rank + rw(e + 8)]

def gate_damage():
    tot = ok = 0
    parts = []
    for tag, (k, s, a0, cd) in CASES.items():
        G, P = load(run('dmg_' + tag, 8200, *CLEAN, 'FF_SPAWN=4152:%d:%d:0:128:0:4' % (k, s)))
        prev = None; n = m = 0
        for f in sorted(P):
            c = P[f]['c']; h = w(c, 24)
            if prev is not None and h < prev and P[f].get(7) is not None and s16(h) > -100:
                n += 1
                atk = c[22]
                if 1 <= atk <= 4 and prev - h == expected_damage(a0, cd, atk): m += 1
            prev = h
        parts.append('%s %d/%d' % (tag, m, n)); tot += n; ok += m
    report('damage', ok, tot, '(' + ', '.join(parts) + ')')

# --- slot geometry: frames waiting at the slot (3(A6) = $10, 4(A6) = 2), kinds 1 and 2 -------------------------------------------------------
def gate_slots():
    SLOT = {i: (s16(rw(0x28084 + 4 * i)), s16(rw(0x28084 + 4 * i + 2))) for i in range(8)}
    tot = okx = oky = 0
    for tag in CASES:
        G, P = load(os.path.join(OUT, 'dmg_%s_rec.txt' % tag))  # produced by the damage gate (same fresh run)
        for f in sorted(P):
            r = P[f].get(7)
            if r is None or r[2] != 2 or r[3] != 0x10 or r[4] != 2: continue
            c = P[f]['c']; dx, dy = SLOT[w(r, 146)]
            ex = s16(w(r, 6)) - (s16(w(c, 6)) + dx)
            ey = s16(w(r, 14)) - (s16(w(c, 14)) - w(c, 90) + dy)
            tot += 1; okx += -8 <= ex <= 8; oky += -12 <= ey <= 4
    report('slots x', okx, tot); report('slots y', oky, tot)

# --- target rule: P2 cloned from P1 at dx = 60, 0, -1, +1 (J at distance 128 from P1; expected P2, P2, P1, P2) -------------------------------
def gate_target():
    want_idx = {60: 2, 0: 2, -1: 1, 1: 2}
    ok = tot = 0
    for kind in (1, 3):
        for dx, want in want_idx.items():
            G, P = load(run('tgt_%d_%d' % (kind, dx), 4200, *CLEAN, 'FF_COPYP2=4151', 'FF_P2DX=%d' % dx, 'FF_SPAWN=4152:%d:0:0:128:0:4' % kind))
            r = P[4158][7]
            got = (w(r, 144) if kind == 1 else r[136] + 1)
            tot += 1; ok += got == want
    report('target', ok, tot, '(kind 1 via $280c8, kind 3 via $3068; P2 wins ties)')

# --- guard: AXL and SLASH, Cody mashing; armed fraction of the $2af88 rolls, dodge state length, blocked hits ----------------------------------
def gate_guard():
    allok = True
    for sub, tag in ((0, 'ma0'), (1, 'ma1')):
        base = 0x2a3ea
        a = base + rw(base + 2 * sub)
        guard = rom[a + 64 + 4]
        rec = run('guard_' + tag, 8000, *CLEAN, 'FF_KEEPEHP=1', 'FF_SPAWN=4152:2:%d:0:128:0:4' % sub, 'FF_PLAN=' + os.path.join(PLANS, 'tap12.lua'),
                  'FF_ADDRS=73e4,7446,742e,2af4c,2afae@d0', 'FF_HIT_OUT=%s/guard_%s.txt' % (OUT, tag), 'FF_HIT_LOG=%s/guard_%s_log.txt' % (OUT, tag),
                  lua='hits.lua', debug=True)
        counts = dict(l.split() for l in open('%s/guard_%s.txt' % (OUT, tag)))
        rolls = [int(l.split()[2], 16) & 0xff for l in open('%s/guard_%s_log.txt' % (OUT, tag)) if l.split()[1] == '2afae']
        armed = sum(1 for x in rolls if x == 255); n = len(rolls); p = guard / 32.0
        sig = (n * p * (1 - p)) ** 0.5
        good = abs(armed - n * p) <= 3 * sig
        allok &= good
        G, P = load(rec)
        runs = []; cur = 0
        for f in sorted(P):
            r = P[f].get(7)
            if r is not None and r[3] == 0x1c: cur += 1
            elif cur: runs.append(cur); cur = 0
        report('guard roll ' + tag, int(good), 1, 'armed %d/%d = %.1f%% (expected %d/32 = %.1f%%); hit attempts %s, blocked %s, landed %s, dodge entries %s' % (
            armed, n, 100.0 * armed / n, guard, 100.0 * p, counts['73e4'], counts['7446'], counts['742e'], counts['2af4c']))
        report('dodge length ' + tag, sum(1 for d in runs if d == 29), len(runs), '(frames in 3(A6) = $1c per dodge; 29 expected)')

# --- determinism: build ff_kinds123 twice (two MAME launches) and compare work RAM; then a resume run against the continuous run -----------
def gate_determinism():
    spawn = 'FF_SPAWN=4152:1:0:0:96:0:4,4152:1:1:0:144:6:4,4152:2:0:0:120:-8:4,4152:2:1:0:176:8:4,4152:3:1:0:200:0:4'
    hashes = []
    for i in (1, 2):
        run('det%d' % i, 4306, *CLEAN, spawn, 'FF_SAVE=ff_kinds123', 'FF_SAVE_FRAME=4300')
        hashes.append(hashlib.sha256(open(os.path.join(OUT, 'ff_kinds123_ram.bin'), 'rb').read()).hexdigest())
    sta = os.path.join(os.environ['AI123_RUN'], 'sta/ffightuc/ff_kinds123.sta')
    report('determinism (2 launches, RAM at frame 4300)', int(hashes[0] == hashes[1]), 1, hashes[0])
    run('chkA', 4308, *CLEAN, spawn, 'FF_SAVE=chkA', 'FF_SAVE_FRAME=4306')
    run('chkB', 4308, *CLEAN, 'FF_LOAD=ff_kinds123', 'FF_SAVE=chkB', 'FF_SAVE_FRAME=4306')
    same = open(os.path.join(OUT, 'chkA_ram.bin'), 'rb').read() == open(os.path.join(OUT, 'chkB_ram.bin'), 'rb').read()
    report('resume from ff_kinds123 vs continuous (RAM at frame 4306)', int(same), 1)
    print('   .sta sha256 %s' % hashlib.sha256(open(sta, 'rb').read()).hexdigest())
    print('   gfx RAM sha256 %s' % hashlib.sha256(open(os.path.join(OUT, 'ff_kinds123_gfxram.bin'), 'rb').read()).hexdigest())
    print('   states are saved under the run directory: copy %s to scratchpad/finalfight/ if it is to be kept' % sta)

GATES = {'names': gate_names, 'damage': gate_damage, 'slots': gate_slots, 'target': gate_target, 'guard': gate_guard, 'determinism': gate_determinism}
if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    todo = sys.argv[1:] or list(GATES)
    for n in todo:
        if n == 'slots' and 'damage' not in todo and 'damage' in GATES: gate_damage()
        GATES[n]()
    bad = [r for r in results if r[1] != r[2]]
    print('SUMMARY:', 'FAIL ' + ', '.join(r[0] for r in bad) if bad else 'all gates pass')
    sys.exit(1 if bad else 0)
