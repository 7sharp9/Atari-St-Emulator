"""posmatch.py <name> <nframes> : camp-marker blit position and pixels against the game's own screen.
For capture frame i (cap.sh <snap> <name> n): stops at every $11f78 entry in the frame drawn after snapshot i (pos.sh), keeps
the first stop of each byte6 6/24 record (A3 in the pool $4cff8..$4d250), reads D0.w/D1.w/D2.w, decodes frame D2 from the
$33000 sheet (json sheet33) and compares each opaque pixel with the screen of snapshot i+1 (json 'ref', x = column in the
compose buffer). Controls on the same frame: the sprite shifted +-1 in x and y (4), and every other frame $110..$115.
Output: per record per frame lines and totals."""
import base64, json, subprocess, sys, re
from pathlib import Path
here = Path(__file__).resolve().parent
root = here
while not (root / 'tools' / 'rdis.py').exists(): root = root.parent
name, n = sys.argv[1], int(sys.argv[2])
cap = here / 'cap'
W, H = 320, 200
def sprite(sheet, idx):
    o = idx * 55; px = {}
    for r in range(11):
        m, p0, p1, p2, p3 = sheet[o + r*5:o + r*5 + 5]
        for x in range(8):
            b = 7 - x
            if not (m >> b) & 1:
                px[(x, r)] = ((p0 >> b) & 1) | (((p1 >> b) & 1) << 1) | (((p2 >> b) & 1) << 2) | (((p3 >> b) & 1) << 3)
    return px
def score(px, ref, x0, y0):
    ok = tot = 0
    for (x, r), c in px.items():
        X, Y = x0 + x, y0 + r
        if 0 <= X < W and 0 <= Y < H:
            tot += 1; ok += ref[Y * W + X] == c
    return ok, tot
tot = {}
for i in range(n - 1):
    st = json.load(open(cap / f'{name}_{i}.json')); sc = json.load(open(cap / f'{name}_{i+1}.json'))
    sheet = base64.b64decode(st['sheet33']); ref = base64.b64decode(sc['ref'])
    out = subprocess.run([str(here / 'pos.sh'), str(cap / f'{name}_{i}.snap'), str(cap / f'{name}_pos{i}'), '60'], capture_output=True, text=True).stdout
    seen = {}; kidx = {}; kk = 0
    for l in out.splitlines():
        m = re.match(r'step (\d+) D0=(\w+) D1=(\w+) D2=(\w+) A3=(\w+)', l)
        if not m: continue
        a3 = int(m.group(5), 16); kk += 1
        if 0x4cff8 <= a3 < 0x4d250 and a3 not in seen:
            kidx[a3] = kk
            seen[a3] = (int(m.group(2), 16) & 0xffff, int(m.group(3), 16) & 0xffff, int(m.group(4), 16))
    recs = {o['addr']: o for o in st['objs']}
    for a3, (d0, d1, d2) in sorted(seen.items()):
        o = recs.get(a3); b7 = o['b7'] if o else -1
        if d0 >= 0x8000: d0 -= 0x10000
        if d1 >= 0x8000: d1 -= 0x10000
        ok, t = score(sprite(sheet, d2), ref, d0, d1)
        # buffer just before and just after this marker's blit (k-th $11f78 entry, return $11612)
        tag = f'{name}_b{i}_{a3:x}'
        rp = cap / (tag + '.repl')
        rp.write_text('\n'.join(['disk scratchpad/powermonger.st'] + ['bp 11f78 3000000'] * kidx[a3] + [f'snap {cap}/{tag}_pre.snap', 'bp 11612 3000000', f'snap {cap}/{tag}_post.snap', 'q']) + '\n')
        env = dict(__import__('os').environ, ATARI_NOTRACE='1')
        subprocess.run(f'dotnet exec bin/Debug/net8.0/M68000.dll resume {cap}/{name}_{i}.snap repl < {rp} > {cap}/{tag}.out 2>&1', shell=True, cwd=root, env=env)
        subprocess.run(['uv', 'run', 'python', 'reversing/powermonger/py/snap2ram.py', f'{cap}/{tag}_pre.snap', f'{cap}/{tag}_post.snap'], cwd=root, capture_output=True)
        pre = (cap / (tag + '_pre.ram')).read_bytes(); post = (cap / (tag + '_post.ram')).read_bytes()
        base = int.from_bytes(post[0x2df7c:0x2df80], 'big')
        def pix(ram, x, y):
            row = base + y * 160 + (x >> 4) * 8; bit = 15 - (x & 15)
            return sum(((ram[row + 2 * p] << 8 | ram[row + 2 * p + 1]) >> bit & 1) << p for p in range(4))
        sp = sprite(sheet, d2)
        # the blit is dst = (dst & mask) | planes: opaque px must equal the sprite colour, masked px unchanged
        o_ok = sum(pix(post, d0 + x, d1 + r) == c for (x, r), c in sp.items())
        m_ok = m_tot = 0
        for r in range(11):
            for x in range(8):
                if (x, r) not in sp:
                    m_tot += 1; m_ok += pix(post, d0 + x, d1 + r) == pix(pre, d0 + x, d1 + r)
        sh_ok = sum(sum(pix(post, d0 + dx + x, d1 + dy + r) == c for (x, r), c in sp.items()) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        wf_ok = sum(sum(pix(post, d0 + x, d1 + r) == c for (x, r), c in sprite(sheet, f).items()) for f in range(0x110, 0x116) if f != d2)
        wf_n = sum(len(sprite(sheet, f)) for f in range(0x110, 0x116) if f != d2)
        bk = tot.setdefault(('buf', a3, b7), [0] * 9)
        bk[0] += 1; bk[1] += o_ok; bk[2] += len(sp); bk[3] += m_ok; bk[4] += m_tot; bk[5] += sh_ok; bk[6] += 4 * len(sp); bk[7] += wf_ok; bk[8] += wf_n
        print(f'  buffer after the blit: opaque px {o_ok}/{len(sp)} = sprite; masked px unchanged {m_ok}/{m_tot}; shifted+-1 {sh_ok}/{4*len(sp)}; other frames {wf_ok}/{wf_n}')
        sh = [score(sprite(sheet, d2), ref, d0 + dx, d1 + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        wf = [score(sprite(sheet, f), ref, d0, d1) for f in range(0x110, 0x116) if f != d2]
        key = (a3, b7)
        k = tot.setdefault(key, [0, 0, 0, 0, 0, 0, 0])
        k[0] += 1; k[1] += ok; k[2] += t; k[3] += sum(s[0] for s in sh); k[4] += sum(s[1] for s in sh); k[5] += sum(s[0] for s in wf); k[6] += sum(s[1] for s in wf)
        print(f'frame {i}: rec {a3:x} b5={o["b5"] if o else "?"} b7=${b7:02x} rot={st["rot_phase"]} D0={d0} D1={d1} D2=${d2:x} (expect ${0x100+b7+((st["rot_phase"]&3) if b7==0x12 else 0):x}): opaque px {ok}/{t} equal; shifted+-1 {sum(s[0] for s in sh)}/{sum(s[1] for s in sh)}; other frames {sum(s[0] for s in wf)}/{sum(s[1] for s in wf)}')
print('TOTALS per (record, byte7): draws, true-frame px eq/total, 4 shifts eq/total, other-frames eq/total')
for key, k in sorted(tot.items(), key=str):
    if key[0] == 'buf':
        print(f'  BUFFER rec {key[1]:x} byte7 ${key[2]:02x}: {k[0]} draws, opaque {k[1]}/{k[2]}; masked unchanged {k[3]}/{k[4]}; shifts {k[5]}/{k[6]}; other frames {k[7]}/{k[8]}'); continue
    a3, b7 = key
    print(f'  rec {a3:x} byte7 ${b7:02x}: {k[0]} draws, {k[1]}/{k[2]}; shifts {k[3]}/{k[4]}; other frames {k[5]}/{k[6]}')
