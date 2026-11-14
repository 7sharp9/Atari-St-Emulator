"""Drive sentences through the real conversation screen and compare the alien's reply with the model.

Run from M68000/:  uv run python reversing/captainblood/py/rules/drive_pairs.py [snap] "WORD WORD ..." ...

For each sentence (vocabulary names, separated by spaces) it starts from the snapshot (default snap/i1.snap, Izwals, no
speech pending), POKES the sentence's icons into the sentence buffer $dc32/$dc34 (labelled poke: the icon grid is not
clicked; the icon of each word is the $60000 token->icon table), moves the pointer to the mouth, clicks it, stops at the
reply engine's entry ($e45a) to save the RAM the engine starts from, lets the click finish and reads the composed
reply tokens ($e412), the alien's icon line ($dc44) and $e3f0.  The model is run on the saved entry RAM; it never sees
the emulator's reply.
"""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cbdata, cbmodel
M68 = cbdata.M68; sys.path.insert(0, os.path.join(M68, 'tools'))
from disassemble import ram_from_snap
b, vocab, races = cbdata.load()
NAME = {n: i + 1 for i, (f, n) in enumerate(vocab)}
def nm(t): return vocab[t - 1][1]
DATA = os.path.join(M68, 'scratchpad/captainblood/rules')
OUT = os.path.join(DATA, 'out', 'pairs'); os.makedirs(OUT, exist_ok=True)

def run(snap, words, tag, pre=()):
    ram = ram_from_snap(snap)
    t2i = ram[0x60000:0x60080]
    toks = [NAME[w] for w in words]
    icons = [t2i[t] for t in toks]
    pre_snap = os.path.join(OUT, f'{tag}_entry.snap')
    if os.path.exists(pre_snap): os.remove(pre_snap)
    L = list(pre) + [f'ww dc32 {len(icons):x}'] + [f'wb {0xdc34 + i:x} {(icons[i] if i < len(icons) else 0):02x}' for i in range(8)]
    L += ['mouse move -7 25', 's 60000', 'mouse down l', 'bp e45a 600000', f'snap {pre_snap}', 's 600000', 'mouse up l', 's 20000',
          'm e412 24', 'm dc44 8', 'm e3f0 2', 'm 61c10 80', 'q']
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], cwd=M68, input='\n'.join(L) + '\n',
                       capture_output=True, text=True, env=env)
    txt = p.stdout
    hexlines = [l.split() for l in txt.splitlines() if re.fullmatch(r'([0-9a-f]{2} ?)+', l.strip()) and len(l.split()) >= 2]
    return txt, hexlines, icons, toks, pre_snap

def model_reply(pre_snap):
    m = cbmodel.Model(bytearray(ram_from_snap(pre_snap)))
    m.d5 = 7; m.d4 = 0
    m.reply_engine()
    out = []; a = 0xe412
    while m.b(a):
        out.append(m.b(a)); a += 1
    return out, m.b(0xe3f0), m

if __name__ == '__main__':
    args = sys.argv[1:]
    snap = os.path.join(DATA, 'snap', 'i1.snap')
    if args and args[0].endswith('.snap'): snap = args.pop(0)
    for k, s in enumerate(args):
        words = s.split()
        txt, hl, icons, toks, pre_snap = run(snap, words, f's{k}')
        if not os.path.exists(pre_snap):
            print(f'{s!r}: engine entry never reached (click refused?)'); print(txt[-600:]); continue
        e412 = [int(x, 16) for x in hl[-4]] if len(hl) >= 4 else []
        reply = []
        for x in e412:
            if x == 0: break
            reply.append(x)
        dc44 = [int(x, 16) for x in hl[-3]][:8]
        e3f0 = [int(x, 16) for x in hl[-2]]
        mo, mflag, m = model_reply(pre_snap)
        ok = (mo == reply) and (mflag == e3f0[0])
        print(f'SAY  {" ".join(words)}  (tokens {toks}, icons {[hex(i) for i in icons]})')
        print(f'ANS  {" ".join(nm(t) if t > 3 else "#"+str(t) for t in reply) or "(nothing)"}   tokens {reply}  e3f0 {e3f0}  dc44 {[hex(i) for i in dc44]}')
        print(f'MODEL {mo} flag {mflag:#x}   {"MATCH" if ok else "MISMATCH"}   (random draws {m.rand_calls})')
