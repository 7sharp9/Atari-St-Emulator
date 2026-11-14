"""chain.py <snap> <games> [out.txt]: an unpoked chain of complete games from a demo-start snapshot ($230c0).  One interactive REPL
session; the demo flies with no input, a breakpoint on the life decrement $25ba0 (100M-step chunks) records each life loss, the last
life (lives = 1 at the stop) ends the game, and `bp 230c0` runs the game over and the attract loop to the next demo start.
Nothing is poked.  Per game it records, at the game's start: RNG $2706e..$27075, the table $27134..$2714b, the high-score table
$25ccc..$25de3 (hash and the first four scores); at each life loss: tick, score, wave; at the game over: tick, score, wave; and steps run.
Output is JSON lines (one per game) plus a readable summary."""
import sys, os, json, subprocess, hashlib
sys.path.insert(0, os.path.dirname(__file__)); import drv
snap, games = sys.argv[1], int(sys.argv[2]); out = sys.argv[3] if len(sys.argv) > 3 else None
env = dict(os.environ, ATARI_NOTRACE='1')
p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=drv.root(), env=env)
def cmd(c, npc=1):
    p.stdin.write(c + '\nr\n'); p.stdin.flush(); lines = []; pcs = 0
    while True:
        l = p.stdout.readline()
        if not l: raise SystemExit('emulator ended')
        lines.append(l.rstrip('\n'))
        if l.startswith('PC:'):
            pcs += 1
            if pcs == npc: return lines
def mem(addr, n):
    rows = drv.mem(cmd(f'm {addr:x} {n:#x}')); return b''.join(rows)
def w(b): return int.from_bytes(b, 'big')
def sw(b): return int.from_bytes(b, 'big', signed=True)
res = []
for g in range(1, games + 1):
    rec = dict(game=g, rng=mem(0x2706e, 8).hex(), table27134=mem(0x27134, 24).hex(), flag=mem(0x62a5f, 1).hex())
    hs = mem(0x25ccc, 280); rec['hs_hash'] = hashlib.sha1(hs).hexdigest()[:8]
    rec['hs_scores'] = [w(hs[28*i:28*i+4]) for i in range(10)]
    rec['losses'] = []; steps = 0
    while True:
        lines = cmd('bp 25ba0 100000000', 2); steps += 100000000
        pc = [l for l in lines if l.startswith('PC:')][0].split()[1]
        if not pc.endswith('25ba0'):
            if steps > 3000000000: raise SystemExit('no death in 3B steps')
            continue
        lives, wave, tick, score = w(mem(0x32a54, 2)), w(mem(0x32a50, 2)), w(mem(0x32a44, 2)), sw(mem(0x2708e, 4))
        rec['losses'].append(dict(tick=tick, score=score, wave=wave, lives_before=lives))
        if lives == 1: rec['over'] = dict(tick=tick, score=score, wave=wave); break
    lines = cmd('bp 230c0 400000000', 2)
    rec['next_start_pc'] = [l for l in lines if l.startswith('PC:')][0].split()[1]
    print(json.dumps(rec), flush=True); res.append(rec)
    if out: open(out, 'a').write(json.dumps(rec) + '\n')
p.stdin.write('q\n'); p.stdin.flush(); p.wait(timeout=30)
