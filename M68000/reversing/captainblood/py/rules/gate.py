"""Differential gate: cbmodel.py against `callcap` of the real engine routines.

Run from M68000/:
    uv run python reversing/captainblood/py/rules/gate.py [--n N] [--break NAME] [--seed S] [--kinds e45a,e6a2,...]

The emulator is the ground truth: for each case the script pokes the case's inputs into i1.snap's RAM (labelled
pokes), runs `callcap <routine>` (which restores the RAM afterwards), then feeds the model the same pre-state RAM
(the model never sees the emulator output) and compares the full memory delta and the exit registers.

Pokes always present (labelled): `w e584 4e714e71` NOPs the `bsr $de74` screen job the no-reply path queues (that
call waits for an interrupt that callcap masks; it only draws, and is out of scope of the model).
"""
import argparse, json, os, random, struct, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cbdata, cbmodel
from cbmodel import V, STATE, TOK, OUT, CLOCK, SEED, Model

M68 = cbdata.M68
sys.path.insert(0, os.path.join(M68, 'tools'))
from disassemble import ram_from_snap

DATA = os.path.join(M68, 'scratchpad/captainblood/rules')
SNAP = os.path.join(DATA, 'snap', 'i1.snap')
OUTD = os.path.join(DATA, 'out')
COM0 = 0x61400
ROI = [(STATE, STATE + 0x100), (COM0 + 0xb10, COM0 + 14826), (0xe3c2, 0xe440), (0xdc32, 0xdc3c),
       (0x7dd36, 0x7dd38), (SEED, SEED + 4), (CLOCK, CLOCK + 2)]
PATCH = {0xe584: bytes.fromhex('4e714e71')}

BREAKS = {  # name -> (attribute, broken value)
    'roll': ('ROLL', 0xe000), 'coin': ('COIN', 0x7fff), 'clock': ('CLKDIV', 60), 'retry': ('RETRY', 6),
    'req_mask': ('REQ', 1), 'ign_mask': ('IGN', 1), 'compose_mask': ('CMASK', 2),
}


def base_ram():
    ram = bytearray(ram_from_snap(SNAP))
    com = open(cbdata.COM, 'rb').read()
    # the snapshot is a running game: the state bit array ($810..$90f) and record flag bytes (used bits) may differ
    _, _, races = cbdata.load()
    allowed = set(range(0x810, 0x910))
    for r in races[:8]:
        a_ = r['A'] - COM0
        while com[a_] != 0xff:
            allowed.add(a_ + 1); a_ += 2 + (com[a_] & 0x1f)
    diff = [i for i in range(len(com)) if ram[COM0 + i] != com[i]]
    assert all(i in allowed for i in diff), 'BLOOD.COM in the snapshot differs from the depacked file beyond state/flags'
    for a, v in PATCH.items():
        ram[a:a + len(v)] = v
    return ram


# ----------------------------------------------------------------------------- stream helpers
class Data:
    def __init__(self):
        self.com, self.vocab, self.races = cbdata.load()
        self.recs = {}
        for r in self.races[:8]:
            recs = cbdata.records(self.com, r)
            # stream B element position for each plain record (every plain record consumes its element count)
            e = 0; out = []
            for (addr, h, f, p) in recs:
                pos = None
                if h & 0xe0 == 0:
                    pos = e
                    i = 0; n = 0
                    while i < len(p):
                        n += 1
                        i += 3 if p[i] <= 3 else 1
                    e += n
                out.append(dict(addr=addr, h=h, f=f, p=p, type=h & 0xe0, len=h & 0x1f, elem=pos))
            self.recs[r['i']] = out
            r['elements'] = e

    def bpos(self, race, elem):
        return self.races[race]['B'] + 3 * (elem // 8), 7 - elem % 8


def tokens_of(p):
    """payload bytes -> list of (token, operand or None)"""
    out = []; i = 0
    while i < len(p):
        if p[i] <= 3:
            out.append((p[i], p[i + 1] << 8 | p[i + 2])); i += 3
        else:
            out.append((p[i], None)); i += 1
    return out


def tok_bytes(toks):
    b = bytearray()
    for t, o in toks:
        b.append(t)
        if t <= 3:
            b += struct.pack('>H', o or 0)
    return bytes(b)


# ----------------------------------------------------------------------------- case generation
KMUL = 3141592621


def seed_for(want, rng, shift):
    """a seed whose next Random value (seed' = seed*K+1, returned seed' >> 8) has (seed' >> shift) low bits == `want`
    (want is the part of seed' above the low `shift` bits; the low bits are random)."""
    low = rng.randrange(0, 1 << shift)
    nxt = ((want << shift) | low) & 0xffffffff
    return ((nxt - 1) * pow(KMUL, -1, 1 << 32)) & 0xffffffff


def cond_words(rec):
    p = rec['p']
    return [p[i] << 8 | p[i + 1] for i in range(0, len(p) - 1, 2)]


def satisfy(pre, rec, setclock):
    """poke the state so the condition record holds"""
    ws = cond_words(rec)
    typ = rec['type']
    start = 0
    if typ != 0x80:
        start = 1
        w = ws[0]
        # a0: holds when w <= clock ; c0: holds when w > clock
        setclock(w if typ == 0xa0 else max(0, w - 1))
    for w in ws[start:]:
        neg = w & 0x8000
        k = (-w) & 0xffff if neg else w
        a = STATE + (k >> 3)
        if neg:
            pre[a] &= ~(1 << (k & 7)) & 0xff
        else:
            pre[a] |= 1 << (k & 7)


def governing(recs, idx):
    j = idx - 1
    while j >= 0 and not recs[j]['type'] & 0x80:
        j -= 1
    chain = []
    while j >= 0 and recs[j]['type'] & 0x80:
        chain.append(recs[j]); j -= 1
    return chain


def make_pre(D, base, rng, race, idx=None, sentence=None, targeted=True, state_density=None, set_vars=True):
    """a pre-state RAM (bytearray copy of base) for the race; returns (pre, info)"""
    pre = bytearray(base)
    r = D.races[race]
    recs = D.recs[race]
    pre[V:V + 4] = struct.pack('>I', r['A']); pre[V + 4:V + 8] = struct.pack('>I', r['B'])
    # state bits
    dens = state_density if state_density is not None else rng.choice([0.05, 0.3, 0.5, 0.8, 0.95])
    for i in range(0x100):
        v = 0
        for b in range(8):
            if rng.random() < dens:
                v |= 1 << b
        pre[STATE + i] = v
    clock = rng.choice([0, 100, 500, 1200, 2399, 5000, 9999, rng.randrange(0, 65536)])
    pre[CLOCK:CLOCK + 2] = struct.pack('>H', clock)
    if idx is not None and targeted and rng.random() < 0.8:
        def setclock(w):
            pre[CLOCK:CLOCK + 2] = struct.pack('>H', min(0xffff, w * 100 + rng.randrange(0, 100)))
        for c in governing(recs, idx):
            satisfy(pre, c, setclock)
    # used flags on a random subset of this race's records
    if rng.random() < 0.5:
        for rec in recs:
            if rng.random() < rng.choice([0.02, 0.2, 0.6]):
                pre[rec['addr'] + 1] |= 0x80
    if idx is not None and rng.random() < 0.15:
        pre[recs[idx]['addr'] + 1] |= 0x80
    if idx is not None and rng.random() < 0.1:
        pre[recs[idx]['addr'] + 1] &= 0x7f
    # sentence
    if sentence is None:
        sentence = b''
    pre[TOK:TOK + 0x20] = bytes(0x20)
    pre[TOK:TOK + len(sentence)] = sentence
    # reply buffer and variables
    for i in range(0x1c):
        pre[OUT + i] = rng.randrange(0, 256) if rng.random() < 0.5 else 0
    if set_vars:
        pre[V + 20:V + 22] = b'\0\0'
        pre[V + 22] = rng.randrange(0, 256)
        pre[V + 24:V + 26] = struct.pack('>H', rng.choice([0, 0, 0, 2]))
        pre[V + 26:V + 28] = struct.pack('>H', rng.choice([7, 7, 7, 3, 1, 0]))
        pre[V + 28] = rng.choice([0, 0x80, 1, 0x81, 0x55])
        pre[0xe3f0] = pre[V + 28]
    pre[0x7dd36:0x7dd38] = struct.pack('>H', rng.randrange(0, 65536))
    pre[SEED:SEED + 4] = struct.pack('>I', rng.randrange(0, 1 << 32))
    pre[0xdc32:0xdc3c] = bytes(rng.randrange(0, 256) for _ in range(10))
    return pre


def sentence_for(D, rng, race, rec):
    toks = tokens_of(rec['p']) if rec else []
    mode = rng.choice(['exact', 'exact', 'shuffle', 'subset', 'extra', 'random', 'wrongop', 'empty'])
    if mode == 'empty' or not toks:
        return b'', 'empty'
    if mode == 'shuffle':
        rng.shuffle(toks)
    elif mode == 'subset':
        keep = [t for t in toks if rng.random() < 0.6] or toks[:1]
        toks = keep
    elif mode == 'extra':
        toks = toks + [(rng.randrange(4, 121), None)]
        rng.shuffle(toks) if rng.random() < 0.5 else None
    elif mode == 'random':
        toks = [(rng.randrange(4, 121), None) for _ in range(rng.randrange(1, 5))]
        if rng.random() < 0.3:
            toks.append((rng.randrange(1, 4), rng.randrange(0, 200)))
    elif mode == 'wrongop':
        toks = [(t, (o + rng.randrange(1, 5)) & 0xffff if o is not None else None) for t, o in toks]
    return tok_bytes(toks[:8]), mode


def gen_cases(D, base, rng, kinds, n):
    cases = []
    races_w = [(0, 40), (3, 25), (1, 20), (4, 6), (6, 6), (2, 1), (5, 1), (7, 1)]
    pool = [r for r, w in races_w for _ in range(w)]

    def pick(race, types):
        recs = D.recs[race]
        c = [i for i, x in enumerate(recs) if x['type'] in types]
        return rng.choice(c) if c else None

    for kind in kinds:
        k = 0
        while k < n[kind]:
            race = rng.choice(pool)
            if kind == 'e45a':
                idx = pick(race, (0,))
                if idx is None:
                    continue
                rec = D.recs[race][idx]
                s, mode = sentence_for(D, rng, race, rec)
                pre = make_pre(D, base, rng, race, idx, s)
                cases.append(dict(kind=kind, name=f'e45a_{k}_r{race}_{mode}', pre=pre, call='e45a', presets={}, info=(race, idx, mode)))
            elif kind == 'e6a2':
                idx = pick(race, (0,))
                if idx is None:
                    continue
                rec = D.recs[race][idx]
                s, mode = sentence_for(D, rng, race, rec)
                pre = make_pre(D, base, rng, race, idx, s, targeted=False)
                a4, d4 = D.bpos(race, rec['elem'])
                pre[V + 20:V + 22] = b'\0\0'
                cases.append(dict(kind=kind, name=f'e6a2_{k}_r{race}_{mode}', pre=pre, call='e6a2',
                                  presets=dict(A5=rec['addr'], A4=a4, D4=d4, D5=rec['len'], A6=V, D0=0), info=(race, idx, mode)))
            elif kind == 'e6a2coin':       # a coin rule with the random draw exactly on, and either side of, the threshold
                recs = D.recs[race]
                c = [i for i, x in enumerate(recs) if x['type'] == 0 and x['f'] & 8 and not x['f'] & 0x80]
                if not c:
                    continue
                idx = rng.choice(c); rec = recs[idx]
                s, mode = sentence_for(D, rng, race, rec)
                pre = make_pre(D, base, rng, race, idx, s, targeted=False)
                for i_ in range(len(recs)):      # the rule is unused so the used-flag test is not what is exercised
                    pass
                pre[rec['addr'] + 1] &= 0x7f
                r16 = rng.choice([0x7ffe, 0x7fff, 0x8000, 0x8001, 0x8002])
                pre[SEED:SEED + 4] = struct.pack('>I', seed_for(r16, rng, shift=16))
                a4, d4 = D.bpos(race, rec['elem'])
                pre[V + 20:V + 22] = b'\0\0'
                cases.append(dict(kind=kind, name=f'e6a2coin_{k}_r{race}_{r16:x}', pre=pre, call='e6a2',
                                  presets=dict(A5=rec['addr'], A4=a4, D4=d4, D5=rec['len'], A6=V, D0=0), info=(race, idx, mode)))
            elif kind == 'e45aroll':        # the state-bit-7 roll with the draw exactly on, and either side of, $f000
                idx = pick(race, (0,))
                if idx is None:
                    continue
                rec = D.recs[race][idx]
                s, mode = sentence_for(D, rng, race, rec)
                pre = make_pre(D, base, rng, race, idx, s)
                v = rng.choice([0xeffe, 0xefff, 0xf000, 0xf001, 0xf002])
                pre[SEED:SEED + 4] = struct.pack('>I', seed_for((rng.randrange(0, 256) << 16 | v), rng, shift=8))
                pre[STATE] &= 0x7f
                cases.append(dict(kind=kind, name=f'e45aroll_{k}_r{race}_{v:x}', pre=pre, call='e45a', presets={}, info=(race, idx, mode)))
            elif kind == 'e58a':
                idx = pick(race, (0x80, 0xa0, 0xc0))
                if idx is None:
                    continue
                rec = D.recs[race][idx]
                pre = make_pre(D, base, rng, race, idx, b'', targeted=False)
                # half the cases: make this condition (and any chained after it) hold
                def setclock(w, pre=pre):
                    pre[CLOCK:CLOCK + 2] = struct.pack('>H', min(0xffff, w * 100 + rng.randrange(0, 100)))
                if rng.random() < 0.5:
                    satisfy(pre, rec, setclock)
                    # also the records chained right after, with probability
                    j = idx + 1
                    while j < len(D.recs[race]) and D.recs[race][j]['type'] & 0x80 and rng.random() < 0.7:
                        satisfy(pre, D.recs[race][j], setclock); j += 1
                if rec['type'] != 0x80 and rng.random() < 0.6:       # clock on, and either side of, the word's boundary
                    w0 = cond_words(rec)[0]
                    pre[CLOCK:CLOCK + 2] = struct.pack('>H', max(0, min(0xffff, w0 * 100 + rng.choice([-1, 0, 99, 100, -100, 1]))))
                pre[V + 20:V + 22] = b'\0\0'
                cases.append(dict(kind=kind, name=f'e58a_{k}_r{race}_t{rec["type"]:02x}', pre=pre, call='e58a',
                                  presets=dict(A5=rec['addr'], D0=rec['type'], D5=rec['len'], A6=V), info=(race, idx, '')))
            elif kind == 'e628':
                idx = pick(race, (0x40,))
                if rng.random() < 0.25:        # the one action record with flag bit 0 (Yukas)
                    race = 3
                    idx = [i for i, x in enumerate(D.recs[3]) if x['type'] == 0x40 and x['f'] & 1][0]
                if idx is None:
                    continue
                rec = D.recs[race][idx]
                pre = make_pre(D, base, rng, race, idx, b'', targeted=False)
                pre[V + 20:V + 22] = b'\0\0'
                cases.append(dict(kind=kind, name=f'e628_{k}_r{race}', pre=pre, call='e628',
                                  presets=dict(A5=rec['addr'], D5=rec['len'], A6=V), info=(race, idx, '')))
            elif kind == 'e22e':
                idx = pick(race, (0,))
                if idx is None:
                    continue
                rec = D.recs[race][idx]
                pre = make_pre(D, base, rng, race, idx, b'', targeted=False)
                a4, d4 = D.bpos(race, rec['elem'])
                pre[V + 8:V + 12] = struct.pack('>I', rec['addr']); pre[V + 12:V + 16] = struct.pack('>I', a4)
                pre[V + 16:V + 18] = struct.pack('>H', rec['len']); pre[V + 18:V + 20] = struct.pack('>H', d4)
                cases.append(dict(kind=kind, name=f'e22e_{k}_r{race}', pre=pre, call='e22e', presets=dict(A6=V), info=(race, idx, '')))
            k += 1
    return cases


# ----------------------------------------------------------------------------- emulator batch
def poke_lines(cur, pre):
    lines = []
    for lo, hi in ROI:
        a = np.frombuffer(bytes(cur[lo:hi]), dtype=np.uint8)
        b = np.frombuffer(bytes(pre[lo:hi]), dtype=np.uint8)
        for i in np.nonzero(a != b)[0]:
            lines.append(f'wb {lo + int(i):x} {int(b[i]):02x}')
    return lines


def run_batch(cases, base, outdir):
    os.makedirs(outdir, exist_ok=True)
    cur = bytearray(base)
    lines = [f'w {a:x} {v.hex()}' for a, v in PATCH.items()]   # labelled poke: NOP the screen job
    for i, c in enumerate(cases):
        lines += poke_lines(cur, c['pre'])
        cur = bytearray(c['pre'])
        pr = ' '.join(f'{k}={v:x}' for k, v in c['presets'].items())
        c['json'] = os.path.join(outdir, f'c{i}.json')
        if os.path.exists(c['json']):
            os.remove(c['json'])
        lines.append(f"callcap {c['call']} 3000000 {c['json']} {pr}".rstrip())
    lines.append('q')
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl'], cwd=M68,
                       input='\n'.join(lines) + '\n', capture_output=True, text=True, env=env)
    open(os.path.join(outdir, 'repl.log'), 'w').write(p.stdout + p.stderr)
    return p


# ----------------------------------------------------------------------------- comparison
def run_model(c, mdl_cls):
    m = mdl_cls(c['pre'])
    m.d5 = 7; m.d4 = 0                         # entry D4/D5 of i1.snap (callcap does not clear them)
    p = c['presets']
    call = c['call']
    m.a5 = p.get('A5', 0); m.a4 = p.get('A4', 0)
    if 'D4' in p: m.d4 = p['D4']
    if 'D5' in p: m.d5 = p['D5']
    if 'D0' in p: m.d0 = p['D0']
    if call == 'e45a':
        m.reply_engine()
    elif call == 'e6a2':
        m.match()
    elif call == 'e58a':
        m.condition()
    elif call == 'e628':
        m.run_actions_from_e628()
    elif call == 'e22e':
        m.compose()
    return m


def compare(c, m, base_pre):
    j = json.load(open(c['json']))
    if not j['outcome'].startswith('returned'):
        return False, f"emulator outcome {j['outcome']}", None
    pre = c['pre']
    emu = {}
    stackhi = j['entrySP']; stacklo = j['entrySP'] - 0x300
    bad_old = 0
    for a, old, new in j['mem']:
        if stacklo <= a < stackhi + 0x10 or 0x900 <= a < 0x940 or 0x4d80 <= a < 0x4dc0:
            continue          # user stack; TOS trap #14 register save area; supervisor exception frame (XBIOS Random)
        if pre[a] != old:
            bad_old += 1
        emu[a] = new
    a = np.frombuffer(bytes(pre), dtype=np.uint8); b = np.frombuffer(bytes(m.r), dtype=np.uint8)
    mod = {int(i): int(b[i]) for i in np.nonzero(a != b)[0]}
    msgs = []
    if bad_old:
        msgs.append(f'{bad_old} callcap old-values differ from the poked pre-state (poke did not take)')
    only_emu = {k: v for k, v in emu.items() if mod.get(k) != v}
    only_mod = {k: v for k, v in mod.items() if emu.get(k) != v}
    if only_emu:
        msgs.append('emu-only/different ' + ' '.join(f'{k:x}:{pre[k]:02x}->{v:02x}' for k, v in sorted(only_emu.items())[:8]))
    if only_mod:
        msgs.append('model-only/different ' + ' '.join(f'{k:x}:{pre[k]:02x}->{v:02x}' for k, v in sorted(only_mod.items())[:8]))
    rn = j['regN']
    regs = {'D4': rn[4], 'D5': rn[5], 'A4': rn[12], 'A5': rn[13]}
    mreg = {'D4': m.d4, 'D5': m.d5, 'A4': m.a4, 'A5': m.a5}
    if c['call'] == 'e22e':
        regs = {}
    if c['call'] == 'e628':
        regs = {'A5': rn[13]}
    if c['call'] == 'e58a':
        regs = {'D5': rn[5], 'A5': rn[13]}
    for k, v in regs.items():
        if (k.startswith('D') and (v & 0xffff) != (mreg[k] & 0xffff)) or (k.startswith('A') and v != mreg[k]):
            msgs.append(f'{k} emu {v:x} model {mreg[k]:x}')
    return (not msgs), '; '.join(msgs), len(emu)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=0)
    ap.add_argument('--seed', type=int, default=20261114)
    ap.add_argument('--break', dest='brk', default=None)
    ap.add_argument('--kinds', default='e45a,e6a2,e58a,e628,e22e,e6a2coin,e45aroll')
    ap.add_argument('--reuse', action='store_true', help='reuse the emulator output in out/<tag>')
    ap.add_argument('--tag', default='main')
    a = ap.parse_args()
    D = Data()
    base = base_ram()
    kinds = a.kinds.split(',')
    defaults = dict(e45a=600, e6a2=300, e58a=250, e628=200, e22e=200, e6a2coin=100, e45aroll=100)
    n = {k: (a.n if a.n else defaults[k]) for k in kinds}
    rng = random.Random(a.seed)
    cases = gen_cases(D, base, rng, kinds, n)
    outdir = os.path.join(OUTD, a.tag)
    if not a.reuse:
        p = run_batch(cases, base, outdir)
    else:
        for i, c in enumerate(cases):
            c['json'] = os.path.join(outdir, f'c{i}.json')
    mdl = cbmodel.Model
    if a.brk:
        attr, val = BREAKS[a.brk]
        mdl = type('Broken', (cbmodel.Model,), {attr: val})
    res = {}
    cov = set()
    fails = []
    for c in cases:
        if not os.path.exists(c['json']):
            res.setdefault(c['kind'], [0, 0])[1] += 1
            fails.append((c['name'], 'no json'))
            continue
        try:
            m = run_model(c, mdl)
        except Exception as e:
            res.setdefault(c['kind'], [0, 0])[1] += 1
            fails.append((c['name'], f'model raised {e!r}'))
            continue
        cov |= m.cov
        ok, msg, ne = compare(c, m, None)
        r = res.setdefault(c['kind'], [0, 0])
        r[1] += 1
        if ok:
            r[0] += 1
        else:
            fails.append((c['name'], msg))
    tot = [sum(v[0] for v in res.values()), sum(v[1] for v in res.values())]
    print('BREAK' if a.brk else 'TRUE', a.brk or '', 'seed', a.seed)
    for k, v in res.items():
        print(f'  {k}: {v[0]}/{v[1]}')
    print(f'  TOTAL {tot[0]}/{tot[1]}')
    for nme, msg in fails[:12]:
        print('  FAIL', nme, msg[:300])
    print('  coverage tags', len(cov))
    open(os.path.join(outdir, 'coverage.txt'), 'w').write('\n'.join(sorted(cov)))


if __name__ == '__main__':
    main()
