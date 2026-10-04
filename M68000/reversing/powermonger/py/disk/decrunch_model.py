"""Model of PowerMonger's `decrunch` ($e2b8) plus an encoder for it (pm147 DISK).

The real routine: A1 = buffer, D0 = packed length. The packed stream sits at A1..A1+D0 and is
decoded IN PLACE, backwards: the last three longs are [bit-buffer seed][checksum seed][unpacked size],
tokens write to -(A2) from A1+size down to A1. Returns normally only when the XOR checksum is 0
(otherwise the real routine spins forever at $e352).

Token grammar (bit = lsr D0; the bit buffer is refilled from -(A0) with a sentinel 1 shifted in at the top):
  0 0 nnn  + (n+1) x 8-bit byte            literal run 1..8
  0 1      + 8-bit off                     copy 2 bytes
  1 00     + 9-bit off                     copy 3
  1 01     + 10-bit off                    copy 4
  1 10     + 8-bit v + 12-bit off          copy v+1
  1 11     + 8-bit v  + (v+9) x 8-bit byte literal run 9..264
  copy: repeat len times { A2 -= 1; mem[A2] = mem[A2 + off] }   (overlap allowed)
All multi-bit fields MSB first.
"""
import os
import random
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("M68000_ROOT") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
WORK = os.path.join(ROOT, "scratchpad", "pm147", "disk")      # extracted disk files + callcap outputs (gitignored)


def disk_files():
    """Directory of the files extracted from scratchpad/powermonger.st (regenerated with tools/extract_disk.py if missing)."""
    d = os.path.join(WORK, "files")
    if not os.path.exists(os.path.join(d, "DATA", "TEXTURES.DAT")):
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "extract_disk.py"),
                        os.path.join(ROOT, "scratchpad", "powermonger.st"), d], check=True)
    return d


class Spin(Exception):
    pass


def decrunch(buf, length, src=None):
    """buf: bytearray whose first `length` bytes are the packed file (in-place decode, mutates buf)."""
    mem = buf
    srcm = src if src is not None else buf
    a0 = length
    state = {"d5": 0, "d0": 0}

    def long_at(a):
        return struct.unpack_from(">I", srcm, a)[0]

    a0 -= 4
    size = long_at(a0)
    a2 = size
    a0 -= 4
    d5 = long_at(a0)
    a0 -= 4
    d0 = long_at(a0)
    d5 ^= d0

    def bit():
        nonlocal d0, d5, a0
        c = d0 & 1
        d0 >>= 1
        if d0 == 0:
            a0 -= 4
            v = long_at(a0)
            d5 ^= v
            c = v & 1
            d0 = (v >> 1) | 0x80000000
        return c

    def bits(n):
        v = 0
        for _ in range(n):
            v = (v << 1) | bit()
        return v

    def lit(n):
        nonlocal a2
        for _ in range(n):
            a2 -= 1
            mem[a2] = bits(8)

    def copy(n, off):
        nonlocal a2
        for _ in range(n):
            a2 -= 1
            mem[a2] = mem[a2 + off]

    # first bit is taken before the loop test: `lsr.l #1,D0` at $e2c6 is the loop head
    while True:
        if bit():
            t = bits(2)
            if t == 2:
                v = bits(8)
                copy(v + 1, bits(12))
            elif t == 3:
                lit(bits(8) + 9)
            else:
                copy(t + 3, bits(9 + t))
        else:
            if bit():
                copy(2, bits(8))
            else:
                lit(bits(3) + 1)
        if not (0 < a2):          # cmpa.l A2,A1 ; blt : continue while A1(=0) < A2
            break
    if d5 != 0:
        raise Spin("checksum")
    return size


def pack(data, rng=None, maxmatch=256):
    """Encoder producing a stream `decrunch` accepts. Greedy, scans from the END of data backwards."""
    n = len(data)
    toks = []   # list of bit-lists in decode order
    p = n       # bytes [p, n) already emitted

    def b(v, k):
        return [(v >> (k - 1 - i)) & 1 for i in range(k)]

    lits = []

    def flush():
        nonlocal lits
        while lits:
            run = lits[:264]
            lits = lits[264:]
            while run:
                if len(run) >= 9:
                    k = min(len(run), 264)
                    toks.append([1, 1, 1] + b(k - 9, 8) + sum([b(x, 8) for x in run[:k]], []))
                    run = run[k:]
                else:
                    toks.append([0, 0] + b(len(run) - 1, 3) + sum([b(x, 8) for x in run], []))
                    run = []

    while p > 0:
        best = (0, 0)
        for off in range(1, min(4095, n - p) + 1):
            # byte at dest d=p-1-k copies mem[d+off]; needs d+off < n  and the source already decoded
            L = 0
            while L < min(p, maxmatch) and p - 1 - L + off < n and data[p - 1 - L] == data[p - 1 - L + off]:
                L += 1
            if L > best[0]:
                best = (L, off)
        L, off = best
        ok = True
        if L >= 5:
            flush(); k = min(L, 256); toks.append([1, 1, 0] + b(k - 1, 8) + b(off, 12)); p -= k
        elif L == 4 and off < 1024:
            flush(); toks.append([1, 0, 1] + b(off, 10)); p -= 4
        elif L >= 3 and off < 512:
            flush(); toks.append([1, 0, 0] + b(off, 9)); p -= 3
        elif L >= 2 and off < 256:
            flush(); toks.append([0, 1] + b(off, 8)); p -= 2
        else:
            ok = False
        if not ok:
            lits.append(data[p - 1]); p -= 1
    flush()
    bitsl = [x for t in toks for x in t]
    nb = len(bitsl)
    k = nb % 32
    N = nb // 32
    # initial word: first k bits LSB-first + sentinel at bit k
    d0 = 1 << k
    for i in range(k):
        d0 |= bitsl[i] << i
    words = []
    pos = k
    for _ in range(N):
        v = 0
        for i in range(32):
            v |= bitsl[pos + i] << i
        words.append(v)
        pos += 32
    chk = d0
    for w in words:
        chk ^= w
    out = b"".join(struct.pack(">I", w) for w in reversed(words)) + struct.pack(">III", d0, chk, n)
    return out


def corpus(seed=1, count=60):
    """Compressible synthetic inputs of varied shape (runs, short alphabets, repeats)."""
    rng = random.Random(seed)
    out = []
    for i in range(count):
        n = rng.randint(1, 900)
        kind = i % 4
        if kind == 0:
            base = bytes(rng.randrange(256) for _ in range(rng.randint(1, 12)))
            d = bytes(base[rng.randrange(len(base))] if rng.random() < .85 else rng.randrange(256) for _ in range(n))
        elif kind == 1:
            d = bytes((j // rng.randint(3, 40)) & 0xff for j in range(n))
        elif kind == 2:
            blk = bytes(rng.randrange(256) for _ in range(rng.randint(2, 60)))
            d = (blk * (n // len(blk) + 1))[:n]
        else:
            d = bytes(0 if rng.random() < .9 else rng.randrange(256) for _ in range(n))
        out.append(d)
    return out


if __name__ == "__main__":
    d = os.path.join(disk_files(), "DATA")
    ok = 0
    for f in sorted(os.listdir(d)):
        raw = open(os.path.join(d, f), "rb").read()
        size = struct.unpack(">I", raw[-4:])[0]
        buf = bytearray(max(size, len(raw)) + 8)
        buf[:len(raw)] = raw
        try:
            decrunch(buf, len(raw))
            print(f, len(raw), "->", size, "checksum 0")
            ok += 1
        except Exception as e:
            print(f, len(raw), "trailer size", size, "FAIL", repr(e))
    # encoder round trip (inputs whose in-place decode corrupts its own stream are reported, not asserted)
    good = bad = 0
    for i, data in enumerate(corpus()):
        pk = pack(data)
        buf = bytearray(max(len(data), len(pk)) + 8)
        buf[:len(pk)] = pk
        oop = bytearray(len(data) + 8)
        decrunch(oop, len(pk), src=pk)          # out of place: must always round trip (encoder check)
        assert bytes(oop[:len(data)]) == data
        try:
            decrunch(buf, len(pk))
            assert bytes(buf[:len(data)]) == data
            good += 1
        except Exception:
            bad += 1
    print("encoder round trip in place: %d ok, %d in-place hazard" % (good, bad))
