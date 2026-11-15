"""chain.py <start.snap> <games> <out.jsonl> [tag]: a chain of K natural Virus attract games, back to back, in one REPL process.
No input, no ESC, no poke after the start snapshot (the carried state at $27134 is written only on the natural game-over path).
Per game it logs: the state carried in at the game start (RNG $2706e..75, queue $27134..$2714b as 24 hex bytes, high-score table
hash and top scores), each life loss (tick, score, wave, lives, step offset into the flight), the game over (tick, score, wave),
flight length in steps (start $230c0 to the last life's decrement at $25ba0), the steps from the game over to the next start
($230c0: game-over screens plus the title/press page idle), and wall seconds.  Score is the signed longword at $2708e (each shot
costs a point, $25752).  The next game starts where this one's `bp 230c0` stops.
One continuous lineage: every game starts from the previous game's actual end (a snapshot of each start is saved under
<out dir>/starts/ for the RAM diff, never resumed from).  Wave = $32a50 (incremented at $20fd0, README), $32a52 = the wave reached,
copied at the game over; $32a4e is the current landscape (0..2), not the wave.
Data convention: python reversing/virus/py/chain/chain.py scratchpad/virus/demo/S1b.snap <games> scratchpad/virus/chain/<run>/chain.jsonl <tag>; start snapshots go to <run>/starts/.
Runs from the repo root (found by walking up to tools/rdis.py).  Output lines are JSON, one per game, appended."""
import sys, os, json, subprocess, hashlib, time, re
p = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(os.path.join(p, 'tools', 'rdis.py')): p = os.path.dirname(p)
root = p
snap, games, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]; tag = sys.argv[4] if len(sys.argv) > 4 else ''
snapdir = os.path.join(os.path.dirname(os.path.abspath(out)), 'starts'); os.makedirs(snapdir, exist_ok=True)
env = dict(os.environ, ATARI_NOTRACE='1')
proc = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=root, env=env)
HEX = re.compile(r'^([0-9a-f]{2} )*[0-9a-f]{2}$')
def cmd(c, npc=1):
    """send c then `r` (registers); read until the npc-th PC: line (a bp stop already prints registers, so bp uses 2)."""
    proc.stdin.write(c + '\nr\n'); proc.stdin.flush(); lines = []
    while True:
        l = proc.stdout.readline()
        if not l: raise SystemExit('emulator ended: ' + '\n'.join(lines[-5:]))
        l = l.rstrip('\n'); lines.append(l)
        if 'REPL error' in l: raise SystemExit(l)
        if l.startswith('PC:'):
            npc -= 1
            if npc == 0: return lines
def mem(addr, n):
    b = b''
    for l in cmd(f'm {addr:x} {n:#x}'):
        if HEX.match(l.strip()): b += bytes.fromhex(l.strip().replace(' ', ''))
    assert len(b) == n, (addr, n, len(b)); return b
def w(b): return int.from_bytes(b, 'big')
def sw(b): return int.from_bytes(b, 'big', signed=True)
def bp(addr, cap):
    """run to $addr; returns (hit, steps, pc)."""
    lines = cmd(f'bp {addr:x} {cap}', 2)
    for l in lines:
        m = re.search(r'hit \(\d+/\d+\) after (\d+) step', l)
        if m: return True, int(m.group(1)), None
        m = re.search(r'gave up after (\d+) step', l)
        if m: return False, int(m.group(1)), None
    raise SystemExit('no bp result: ' + '\n'.join(lines))
for g in range(1, games + 1):
    t0 = time.time()
    rec = dict(tag=tag, game=g, rng=mem(0x2706e, 8).hex(), queue=mem(0x27134, 24).hex(), flag=mem(0x62a5f, 1).hex())
    assert rec['flag'] == 'ff', 'not an attract game'
    rec['w32a4e'] = w(mem(0x32a4e, 2)); rec['w32a50'] = w(mem(0x32a50, 2)); rec['w32a52'] = w(mem(0x32a52, 2))
    rec['start_snap'] = os.path.join(snapdir, f'{tag}_g{g:03d}.snap'); cmd(f'snap {rec["start_snap"]}')
    hs = mem(0x25ccc, 280); rec['hs_hash'] = hashlib.sha1(hs).hexdigest()[:8]; rec['hs_top'] = [w(hs[28*i:28*i+4]) for i in range(10)]
    rec['losses'] = []; flight = 0
    while True:
        hit, n, _ = bp(0x25ba0, 1000000000); flight += n
        if not hit:
            if flight > 6000000000: raise SystemExit('no death in 6G steps')
            continue
        lives, wave, tick, score = w(mem(0x32a54, 2)), w(mem(0x32a50, 2)), w(mem(0x32a44, 2)), sw(mem(0x2708e, 4))
        rec['losses'].append(dict(tick=tick, score=score, wave=wave, lives=lives, step=flight))
        if lives == 1:
            rec['over'] = dict(tick=tick, score=score, wave=wave, w32a4e=w(mem(0x32a4e, 2)), w32a52=w(mem(0x32a52, 2))); rec['flight_steps'] = flight; break
    hit, n, _ = bp(0x230c0, 1000000000); assert hit, 'next demo start not reached'
    rec['over_to_next_steps'] = n; rec['wall_s'] = round(time.time() - t0, 1)
    open(out, 'a').write(json.dumps(rec) + '\n'); print(json.dumps(rec), flush=True)
proc.stdin.write('q\n'); proc.stdin.flush(); proc.wait(timeout=60)
