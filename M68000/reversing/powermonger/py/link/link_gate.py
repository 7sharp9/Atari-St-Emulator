"""link_gate.py: differential gate for the $6eb6 link handshake (PowerMonger 147th pass, LINK).

The MFP USART is not modelled by the emulator (TSR bit 7 never sets, the TBE/RBF interrupts never fire), so the
real routine is driven with a scripted peer: at every `$1c3dc` stop (just after `$1c390` wrote a byte to UDR) the
script clears the busy flag `$5836c` and appends one peer byte to the receive ring `$58368`.
  sends 1, 2   '?' ($71fc)  -- the peer's '?' is fed after send 1
  sends 3..714 the 712 bytes $580a0..$58367 of the local game block; the peer's block is fed byte for byte
  send 715     the checksum (8-bit sum of the sent bytes); the peer's checksum is fed
Then the merge tail ($706c..$7198) runs for real and RAM is compared with a Python model of it.

Scenarios: A peer side 2 > local 1 (local keeps its block), B local 2, peer 1 (local adopts the peer block),
C peer side == local side (error 't', $71fd = $74), D bad peer checksum (error 'b', $71fd = $62).
usage: cd M68000 && uv run python reversing/powermonger/py/link/link_gate.py [A|B|C|D ...]
Input: scratchpad/pm147/link/mp_trying.snap (login dialog open, CONNECT clicked, PC=$1c39e). If missing it is regenerated
from pm123/win/m1_ready.snap: mp1.cmds (poke $71fe, dialog opens, snap mp_dialog.snap) then mp2.cmds (real CONNECT click,
snap mp_trying.snap); both REPL scripts sit beside this file.
"""
import os, re, subprocess, sys, random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUT = os.path.join(ROOT, 'scratchpad', 'pm147', 'link')      # snapshots and run_*.out
os.makedirs(OUT, exist_ok=True)
SNAP = os.path.join(OUT, 'mp_trying.snap')       # CONNECT clicked, PC=$1c39e waiting to send the first '?'
BASE, NBASE = 0x57ff0, 1300                       # RAM window compared
BLK, BLKLEN = 0x580a0, 0x2c8                      # the exchanged block $580a0..$58367
HEX = re.compile(r'^([0-9a-f]{2} )*[0-9a-f]{2}$')


LAST_ERR = ''


def emu(lines, cap_note=''):
    global LAST_ERR
    p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl'],
                       input='\n'.join(lines) + '\nq\n', text=True, capture_output=True, cwd=ROOT,
                       env=dict(os.environ, ATARI_NOTRACE='1'))
    LAST_ERR = p.stderr
    return p.stdout


def hexstream(out):
    b = []
    for ln in out.splitlines():
        ln = ln.strip()
        if HEX.match(ln):
            b += [int(x, 16) for x in ln.split()]
    return bytes(b)


def w16(m, a):  return (m[a - BASE] << 8) | m[a - BASE + 1]


def model(mem, myside, R):
    """mem: bytearray of RAM window BASE..; R: received block (712 bytes). Returns (expected mem, status)."""
    m = bytearray(mem)
    o = lambda a: a - BLK
    R = bytearray(R)
    peer = (R[o(0x582f2)] << 8) | R[o(0x582f2) + 1]
    if peer == myside:
        return None, 't'
    # flags: 5 entries at $582f4, slots at $58016 (6 bytes each, state at +4)
    for i in range(5):
        m[0x58016 + 6 * i + 4 - BASE] = 0
        d2 = R[o(0x582f4) + i]
        m[0x582f4 + i - BASE] |= d2
        R[o(0x582f4) + i] = m[0x582f4 + i - BASE]
        if m[0x582f4 + i - BASE] != 0:
            m[0x58016 + 6 * i + 4 - BASE] = 4
    m[0x58016 + 6 * myside + 4 - BASE] = 6
    m[0x58016 + 6 * peer + 4 - BASE] = 8
    m[0x57ffe - BASE], m[0x57ffe - BASE + 1] = 0, myside                        # $57ffe := $582f2
    # _restore ($12e34): 64 default-name bytes from $a29c to $582f9, then the saved name $58339 into side myside's slot
    m[0x582f9 - BASE:0x582f9 - BASE + 64] = mem_at(mem, 0xa29c, 64)
    nm = cstr(m, 0x58339)
    dst = 0x582e9 + 16 * myside
    m[dst - BASE:dst - BASE + len(nm) + 1] = nm + b'\0'
    # peer's saved name (from its block) into the peer side's slot
    pn = bytes(R[o(0x58339):]).split(b'\0')[0]
    dst = 0x582e9 + 16 * peer
    m[dst - BASE:dst - BASE + len(pn) + 1] = pn + b'\0'
    if peer < myside:                                                         # bgt $7178 skips when peer > local
        R[o(0x582f9):o(0x582f9) + 64] = m[0x582f9 - BASE:0x582f9 - BASE + 64]
        m[BLK - BASE:BLK - BASE + BLKLEN] = R
    ptr = 0x58016 + 6 * myside
    m[0x58034 - BASE:0x58038 - BASE] = ptr.to_bytes(4, 'big')
    return m, 'ok'


A29C = {}
def mem_at(mem, a, n):
    return A29C['d'][a - 0xa29c:a - 0xa29c + n]


def cstr(m, a):
    i = a - BASE
    j = i
    while m[j]:
        j += 1
    return bytes(m[i:j])


def ensure_snap():
    if os.path.exists(SNAP):
        return
    for cmds, src in (('mp1.cmds', 'scratchpad/pm123/win/m1_ready.snap'), ('mp2.cmds', 'scratchpad/pm147/link/mp_dialog.snap')):
        subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', src, 'repl'],
                       stdin=open(os.path.join(HERE, cmds)), capture_output=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'))
    assert os.path.exists(SNAP), 'could not regenerate mp_trying.snap'


def main():
    ensure_snap()
    which = sys.argv[1:] or ['A', 'B', 'C', 'D']
    out = emu([f'm {BASE:x} {NBASE}', 'm a29c 64'])
    s = hexstream(out)
    base, A29C['d'] = bytearray(s[:NBASE]), s[NBASE:NBASE + 64]
    assert len(s) == NBASE + 64, len(s)
    mine = bytes(base[BLK - BASE:BLK - BASE + BLKLEN])
    print('local side word $582f2 =', w16(base, 0x582f2), ' flags $582f4 =', list(base[0x582f4 - BASE:0x582f4 - BASE + 5]),
          ' saved name $58339 =', cstr(base, 0x58339))
    ok_all = True
    for sc in which:
        myside = 2 if sc == 'B' else 1
        peer = {'A': 2, 'B': 1, 'C': 1, 'D': 2}[sc]
        rnd = random.Random(7 + ord(sc))
        P = bytearray(rnd.randrange(256) for _ in range(BLKLEN))
        o = lambda a: a - BLK
        P[o(0x582f2)], P[o(0x582f2) + 1] = 0, peer
        for i, v in enumerate([0, 0, 0, 1, 0]):
            P[o(0x582f4) + i] = v
        P[o(0x58339):o(0x58339) + 16] = b'PEERLORD\0' + bytes(7)
        P[o(0x582f9):o(0x582f9) + 64] = (b'Peer A\0' + bytes(9) + b'Peer B\0' + bytes(9) + b'Peer C\0' + bytes(9) + b'Peer D\0' + bytes(9))
        peer_chk = sum(P) & 255
        sent_chk = (peer_chk + (1 if sc == 'D' else 0)) & 255
        lines = []
        ring = bytearray(208)

        def feed(idx, byte):                                    # aligned longword write of the ring cell
            ring[idx] = byte
            a = idx & ~3
            return f'w {0x58374 + a:x} {ring[a]:02x}{ring[a + 1]:02x}{ring[a + 2]:02x}{ring[a + 3]:02x}'

        if myside != 1:
            lines.append(f'w 582f2 {myside:04x}{base[0x582f4 - BASE]:02x}{base[0x582f5 - BASE]:02x}')
        lines.append('w fffa2a 00010081')                  # TSR bit 7 (buffer empty) so $1c390 can send
        total = 2 + BLKLEN + 1
        for k in range(1, total + 1):
            lines.append('bp 1c3dc 12000000')
            if k == 1:
                lines += [feed(0, 0x3f), 'w 5836a 00010000']
            elif k == 2:
                lines += ['w 5836c 000004b0']
            elif k <= 2 + BLKLEN:
                j = k - 3
                lines += [feed(j % 201, P[j]), f'w 5836a {(j + 1) % 201:04x}0000']
            else:
                j = BLKLEN
                lines += [feed(j % 201, sent_chk), f'w 5836a {(j + 1) % 201:04x}0000']
        if sc in 'AB':
            lines += ['bp 7198 60000000', f'm {BASE:x} {NBASE}', 'r']
        else:
            lines += ['s 3000000', 'm 71fc 4', 'r']
        out = emu(lines)
        open(os.path.join(OUT, f'run_{sc}.out'), 'w').write(out)
        # sent stream: D1 low byte at each stop
        d1 = [int(x, 16) & 255 for x in re.findall(r'D0:[0-9A-Fa-f]{8} D1:([0-9A-Fa-f]{8})', out)]
        sent = bytes(d1[:total])
        mine_sc = bytes(patch(base, myside)[BLK - BASE:BLK - BASE + BLKLEN])
        chk_mine = sum(mine_sc) & 255
        exp = b'??' + mine_sc + bytes([chk_mine])
        sres = f'sent stream {len(sent)}/{total} bytes, match={sent == exp}'
        if sc in 'AB':
            s = hexstream(out)
            got = bytearray(s[-NBASE:])
            exp_mem, st = model(base if myside == 1 else patch(base, myside), myside, P)
            lim = 0x58368 - BASE                                  # the ring and the received copy lie above
            diffs = [hex(BASE + i) for i in range(lim) if got[i] != exp_mem[i]]
            # $58034 and the slot table are in the window; $584c4.. is outside it
            res = (sent == exp) and not diffs
            print(f'{sc}: {sres}; RAM $57ff0..$58367 vs model: {len(diffs)} differing', diffs[:8], 'PASS' if res else 'FAIL')
        else:
            tail = hexstream(out)[-4:]
            print(f'{sc}: {sres}; $71fc..: {tail.hex()} (expect fd byte {"74" if sc == "C" else "62"})',
                  'PASS' if (sent == exp or sc == 'D') and tail[1] == (0x74 if sc == 'C' else 0x62) else 'FAIL')
            res = tail[1] == (0x74 if sc == 'C' else 0x62)
        ok_all &= res
    print('ALL PASS' if ok_all else 'SOME FAIL')


def patch(base, side):
    b = bytearray(base)
    b[0x582f2 - BASE], b[0x582f2 - BASE + 1] = 0, side
    return b


if __name__ == '__main__':
    main()
