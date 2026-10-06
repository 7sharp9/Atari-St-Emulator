"""Minimal GDB Remote Serial Protocol client (stdlib only, ack mode) for MAME's gdbstub.
Usage as a module: c = RSP(port); c.cmd('qSupported'); c.regs(); c.mem(addr, n); c.cont() ...
"""
import socket, time

def cs(b): return sum(b) & 0xff

class RSP:
    def __init__(self, port, host='127.0.0.1', timeout=30, verbose=False):
        self.s = socket.create_connection((host, port), timeout=timeout)
        self.s.settimeout(timeout)
        self.buf = b''
        self.verbose = verbose
        self.noack = False

    def _fill(self, timeout=None):
        if timeout is not None: self.s.settimeout(timeout)
        d = self.s.recv(65536)
        if not d: raise EOFError('closed')
        self.buf += d

    def send(self, payload):
        if isinstance(payload, str): payload = payload.encode()
        pkt = b'$' + payload + b'#%02x' % cs(payload)
        if self.verbose: print('->', pkt[:100])
        self.s.sendall(pkt)

    def recv_packet(self, timeout=30):
        """Return payload bytes of next $..#cs packet (acks it)."""
        self.s.settimeout(timeout)
        while True:
            i = self.buf.find(b'$')
            if i >= 0:
                j = self.buf.find(b'#', i)
                if j >= 0 and len(self.buf) >= j + 3:
                    payload = self.buf[i+1:j]
                    self.buf = self.buf[j+3:]
                    if not self.noack: self.s.sendall(b'+')
                    if self.verbose: print('<-', payload[:100])
                    return payload
            # drop leading acks
            if i < 0 and self.buf: self.buf = b''
            self._fill()

    def cmd(self, payload, timeout=30):
        self.send(payload)
        return self.recv_packet(timeout)

    def init(self):
        """Mandatory with MAME's stub: `g`/`p` return E01 until target.xml has been read."""
        self.cmd('qSupported')
        self.xml = self.cmd('qXfer:features:read:target.xml:0,fff')
        return self.xml

    # helpers
    def regs(self):
        return self.cmd('g').decode()

    def mem(self, addr, n, chunk=0x1000):
        out = b''
        while n > 0:
            k = min(n, chunk)
            r = self.cmd('m%x,%x' % (addr, k))
            if r[:1] == b'E': raise IOError('m %x,%x -> %s' % (addr, k, r))
            out += bytes.fromhex(r.decode())
            addr += k; n -= k
        return out

    def write(self, addr, data):
        return self.cmd('M%x,%x:%s' % (addr, len(data), data.hex()))

    def bp(self, addr, kind=2, typ=0):
        return self.cmd('Z%d,%x,%x' % (typ, addr, kind))

    def unbp(self, addr, kind=2, typ=0):
        return self.cmd('z%d,%x,%x' % (typ, addr, kind))

    def cont(self, timeout=60):
        """Send c and wait for a stop reply."""
        self.send('c')
        return self.recv_packet(timeout)

    def step(self, timeout=30):
        return self.cmd('s', timeout)

    def interrupt(self):
        self.s.sendall(b'\x03')

def u32(h): return int(h, 16)
