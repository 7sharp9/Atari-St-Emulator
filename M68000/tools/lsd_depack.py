"""Depack Zuul menu-disk `LSD!` files (a byte-buffer Pack-Ice 2.x bitstream).

usage: lsd_depack.py <in> <out>
       lsd_depack.py --all <dir> <outdir>     (every LSD!/ICE! file under <dir>, tree kept)

Ground truth is the 68000 depacker in PACT.PRG (after two passes of its own
"ZUUL & HIDDEN PACKER" stub; text offset $1f6 checks LSD!, $2d4 decodes).

Header: 'LSD!', unpacked size, N where the packed file is 4+N bytes long. The
stream is read backwards from the file end: if the word at end-2 is negative
one more byte is skipped, then one byte is the first bit buffer. Bits come out
of the byte MSB-first through `lsl.b`; a zero result reloads the next byte with
a 1 shifted into bit 0 (sentinel). Literal bytes come from the same byte stream.
Decoding stops when the source pointer reaches the first data byte (header+12).

ICE! files are accepted with the header order packed-length (incl. header),
unpacked-length and the same bitstream: that is from memory of Pack-Ice 2.31,
not checked against code (no ICE! file on this disk).
"""
import os
import struct
import sys

LIT_BITS, LIT_ADD = (10, 3, 2, 2), (14, 7, 4, 1)          # PACT $33e
LEN_BITS, LEN_ADD = (10, 2, 1, 0, 0), (10, 6, 4, 3, 2)    # PACT $3a6
OFF_BITS, OFF_ADD = (11, 4, 7), (0x120, 0x000, 0x020)     # PACT $3ea (bits+1 read)


def header(buf):
    magic = buf[:4]
    a, b = struct.unpack('>II', buf[4:12])
    if magic == b'LSD!':
        return a, 4 + b                  # unpacked, packed end offset
    if magic == b'ICE!':
        return b, a                      # inferred Ice 2.31 order
    return None


def depack(buf):
    hdr = header(buf)
    if hdr is None:
        raise ValueError('no LSD!/ICE! magic')
    size, end = hdr
    if end > len(buf):
        raise ValueError(f'packed end {end} beyond file length {len(buf)}')
    src = buf
    p = end - 2
    if src[p] & 0x80:                    # tst.w -(A0) / bpl / subq.l #1,A0
        p -= 1
    p -= 1
    d0 = src[p]                          # initial bit buffer (has its own sentinel)
    out = bytearray(size)
    q = size

    def bit():
        nonlocal d0, p
        d0 <<= 1
        c = d0 >> 8
        d0 &= 0xff
        if d0 == 0:                      # lsl.b gave 0: reload, roxl in X(=1)
            p -= 1
            v = (src[p] << 1) | 1
            c = v >> 8
            d0 = v & 0xff
        return c

    def bits(n):
        v = 0
        for _ in range(n):
            v = (v << 1) | bit()
        return v

    while True:
        if bit():                        # literal run
            n = 0
            if bit():
                for i in (3, 2, 1, 0):
                    n = bits(LIT_BITS[i])
                    if i == 0 or n != (1 << LIT_BITS[i]) - 1:
                        n += LIT_ADD[i]
                        break
            for _ in range(n + 1):
                p -= 1
                q -= 1
                if q < 0:
                    raise ValueError('literal overruns output')
                out[q] = src[p]
        if p <= 12:                      # cmpa.l A3,A0 / ble done
            break
        i = 3                            # match length
        while i >= 0 and bit():
            i -= 1
        i += 1
        n = (bits(LEN_BITS[i]) if LEN_BITS[i] else 0) + LEN_ADD[i]
        if n == 2:
            off = bits(9) + 64 if bit() else bits(6)
        else:
            j = 1
            while j >= 0 and bit():
                j -= 1
            j += 1
            off = bits(OFF_BITS[j] + 1) + OFF_ADD[j]
        for _ in range(n):
            q -= 1
            if q < 0 or q + off + n >= size:
                raise ValueError('match out of range')
            out[q] = out[q + off + n]
    depack.end_pos = p                   # source position at stop (12 = exact)
    if q != 0:
        raise ValueError(f'stream ended with {q} of {size} bytes unwritten')
    return bytes(out)


def one(src, dst):
    buf = open(src, 'rb').read()
    data = depack(buf)
    assert len(data) == header(buf)[0]
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    open(dst, 'wb').write(data)
    return len(buf), len(data)


def main(argv):
    if len(argv) == 4 and argv[1] == '--all':
        root, outdir, bad = argv[2], argv[3], 0
        for dp, _, names in sorted(os.walk(root)):
            for nm in sorted(names):
                f = os.path.join(dp, nm)
                with open(f, 'rb') as fh:
                    if header(fh.read(12) + b'\0' * 12) is None:
                        continue
                rel = os.path.relpath(f, root)
                try:
                    pk, un = one(f, os.path.join(outdir, rel))
                    print(f'{rel}\t{pk}\t{un}')
                except (ValueError, AssertionError, IndexError) as e:
                    print(f'{rel}\tFAILED: {e}', file=sys.stderr)
                    bad += 1
        return 1 if bad else 0
    if len(argv) == 3:
        try:
            pk, un = one(argv[1], argv[2])
        except (ValueError, AssertionError, IndexError) as e:
            print(f'FAILED: {e}', file=sys.stderr)
            return 1
        print(f'{argv[1]}\t{pk}\t{un}')
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
