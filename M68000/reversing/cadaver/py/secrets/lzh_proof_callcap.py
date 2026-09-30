"""Proof that cad_lzh.py == the game's own expander $0118ec, bit for bit, on real disk blocks.

Start snapshot: scratchpad/cadaver/gameplay_empire.snap.  For each disk block given (default: the 5 level-0 and the
4 lzh level-1 blocks small enough to poke) it (1) pokes the on-disk stream into free RAM at $80000 with REPL `w`
longwords, (2) `callcap 118ec` with A0=stream (after the 4-byte length), A1=$a0000 (dest), D0=expanded length,
(3) rebuilds the destination image from the callcap delta and compares it with cad_lzh.decode_block().
Prints one line per block: '<name> expanded N bytes: M match' (expected M == N for every block).

Run from M68000/:  uv run python reversing/cadaver/py/secrets/lzh_proof_callcap.py [max_poke_bytes=70000]
Needs no build; uses bin/Debug/net8.0/M68000.dll with ATARI_NOTRACE=1.
"""
import json, os, struct, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
OUT = os.path.join(os.path.abspath(os.path.join(here, '..', '..', '..', '..')), 'scratchpad/cadaver/secrets_out'); os.makedirs(OUT, exist_ok=True)
from cad_lzh import decode_block
M68 = os.path.abspath(os.path.join(here, '..', '..', '..', '..'))
REPO = os.path.dirname(M68)
DISK = os.path.join(REPO, 'Cadaver', 'Cadaver (1990)(Image Works)[cr Empire][one disk].st')
SNAP = os.path.join(M68, 'scratchpad/cadaver/gameplay_empire.snap')
d = open(DISK, 'rb').read()
ents = [struct.unpack_from('>HH', d, 400 * 512 + 0x10 + 4 * i) for i in range(10)]
maxpoke = int(sys.argv[1]) if len(sys.argv) > 1 else 70000
SRC, DST = 0x80000, 0xa0000
names = {}
for slot in (0, 1):
    for k in range(5):
        if k == 2: continue  # resource 2 is stored raw (no length+stream)
        names[(slot, k)] = ents[slot * 5 + k]
tot_ok = 0
for (slot, k), (s, c) in names.items():
    blk = d[s * 512:(s + c) * 512]; n = struct.unpack('>I', blk[:4])[0]
    if len(blk) > maxpoke: print('slot%d res%d: skipped (%d bytes > maxpoke)' % (slot, k, len(blk))); continue
    py, used = decode_block(blk)
    data = blk + b'\0' * (-len(blk) % 4)
    cmds = ['w %x %s' % (SRC + i, data[i:i + 4].hex()) for i in range(0, len(data), 4)]
    out = os.path.join(OUT, 'lzh_cc_s%dr%d.json' % (slot, k))
    cmds += ['callcap 118ec 60000000 %s D0=%x A0=%x A1=%x' % (out, n, SRC + 4, DST), 'q']
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl', '--disk-a', DISK],
                       input='\n'.join(cmds) + '\n', text=True, capture_output=True, cwd=M68, env=env)
    res = json.load(open(out))
    img = bytearray(n)
    for a, old, new in res['mem']:
        if DST <= a < DST + n: img[a - DST] = new
    match = sum(x == y for x, y in zip(img, py))
    print('slot%d res%d (sector %d, %d sectors): expanded %d bytes: %d match; callcap steps=%d outcome=%s' % (slot, k, s, c, n, match, res['steps'], res['outcome']))
