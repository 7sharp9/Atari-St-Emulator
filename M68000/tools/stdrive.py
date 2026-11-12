"""Game driver library over one `stserver` process (`stclient.py`), with the evidence rules as defaults and a
journal that replays every drive.

    import sys; sys.path.insert(0, '<root>/tools'); import stdrive as sd
    d = sd.Drive(root, journal='out/run.jsonl', fields={'hero_x': (0x1a574, 2)}, period=24000)
    d.load(snap, disk)                       # `disk` is required, as in stserver (None for a disk-less snapshot)
    d.hold(sd.Joy(0x08), polls=3)            # from the next VBL boundary, held 3 poll periods, then released
    d.tap(sd.Key(0x39))                      # make, held one poll period plus half a frame, break, one period released
    r = d.wait_until(0x22803, 0xff, budget=2_000_000)    # r.ok, r.steps, r.value
    ab = d.ab(lambda d: d.hold(sd.Joy(0x08), polls=4), budget=200_000)
    print(ab.report())                       # both end states and the named fields that differ
    d.save('out/end.snap'); d.close()
    saves = sd.replay('out/run.jsonl', 'out/replay')     # re-runs the journal; [(original save, replayed save)]

Timing model (DEVELOPING.md; `instructionsPerFrame` in `Program.fs`): the VBL is raised by `AtartSt.Step` when the
step counter is a multiple of `FRAME` = 12,000 steps. `hold`/`tap` apply their input at such a step (just before that
VBL) unless `align=False`. A game's poll period is a parameter (`period=` on the Drive or per call): Impossamole reads
the stick about every 24,000-30,000 steps, so a hold shorter than that is a sample, not an input (CLAUDE.md,
"Evidence rules": a hold longer than the game's poll cycle). `hold` refuses a hold that does not cover at least one
full period unless `allow_short=True`.

Inputs: `Joy(bits, port=1)` (IKBD joystick packet `$ff bits` for port 1, `$fe` for port 0; release is the packet with
bits 0), `Key(scancode)` (make, then break = code | $80), `Raw(press_groups, release_groups)`. A packet goes to the
server as one `kbd` call; `Joy(..., split=True)` sends the header and the state byte as two calls, as a REPL script's
`kbd ff` / `kbd 09` lines do. Only the one-call form updates the MMU's copy of the stick state that an IKBD
interrogation reads (`MMU.EnqueueIkbd`); in Impossamole's boss fight both forms end in byte-identical snapshots.

Fields: a plain dict `{name: (addr, width)}`; `d.field(name)` decodes big-endian unsigned (`signed=True` for signed),
`d.fields()` all of them. Reads go through a cache that any input, step, restore or load clears, so a script may read
the same block many times per step for the cost of one RPC (`prefetch(addr, n)` loads a block once).

Journal (always on: default `./scratchpad/stdrive/journal/<time>-<pid>.jsonl` under the cwd): one JSON object per
line, `op` in load / step / kbd / mouse / poke / set_reg / disk / fork / restore / save / note. Every op carries `at`,
the absolute step counter before it, and `load` the SHA-1 of the snapshot and disk. Consecutive steps are coalesced;
a `run` that stopped early (stop watch, breakpoint, until_pc) is journalled as the steps it actually ran, so a replay
needs no watch. `replay()` re-issues the ops, checks every `at` against the journal (a mismatch raises), and writes each
`save` into its own output directory, never over the original path.

Recordings (`Drive(..., record=<dir>, every=500_000, keep=16)`): stserver's recordings refuse `load` and `restore`
while active, so the Drive records each linear stretch as its own segment: it starts `record_start` (with `dir`, so
the checkpoints and journal go to disk) after every `load` and `restore`, stops it before the next one and at `close`,
and lists the segments in `d.segments` (`dir`, `base`, `end`, server `id`) and in `<dir>/segments.json`. A segment is
a directory `record_load` reads back in a fresh process, so `last_writer`, `replay_to` and `tools/provenance.py
--recording <seg dir>` slice the drive after it has ended. A segment that wrote to disk A is kept in memory only and
cannot be loaded back (`record_load` refuses it). The journal notes each segment; `replay()` does not record.
"""
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stclient import StServer

FRAME = 12000          # steps per VBL: `instructionsPerFrame` in Program.fs

# Methods that change machine state: only the Drive's own wrappers may send them, so the journal stays complete.
_STATEFUL = {'load', 'boot', 'step', 'run', 'hits', 'poke', 'set_reg', 'kbd', 'mouse', 'disk', 'restore', 'replay_to',
             'last_writer', 'first_divergence'}


def _sha1(path):
    if path is None:
        return None
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ---- inputs -------------------------------------------------------------------------------------------------------

class Raw:
    """An input as IKBD byte groups: each group is one `kbd` call."""
    def __init__(self, press, release=(), name=None):
        self.press_groups = [list(g) for g in press]
        self.release_groups = [list(g) for g in release]
        self.name = name or 'raw'

    def __repr__(self):
        return self.name


class Joy(Raw):
    """Joystick state packet. bits: 1 up, 2 down, 4 left, 8 right, $80 fire. port 1 = header $ff, port 0 = $fe."""
    def __init__(self, bits, port=1, split=False):
        h = 0xff if port == 1 else 0xfe
        mk = (lambda b: [[h], [b]]) if split else (lambda b: [[h, b]])
        super().__init__(mk(bits), mk(0), f'Joy({bits:#04x}{", split" if split else ""})')
        self.bits = bits


class Key(Raw):
    """Keyboard make code; release is the break code (code | $80)."""
    def __init__(self, code):
        super().__init__([[code]], [[code | 0x80]], f'Key({code:#04x})')


# ---- results ------------------------------------------------------------------------------------------------------

class Wait:
    def __init__(self, ok, steps, value, stops):
        self.ok, self.steps, self.value, self.stops = ok, steps, value, stops

    def __repr__(self):
        return f'Wait(ok={self.ok}, steps={self.steps}, value={self.value:#x}, stops={self.stops})'


class AB:
    """Result of `Drive.ab`: `a` the input arm, `b` the control, each {'step', 'fields': {name: bytes}, 'snap'}; `diff`
    the named ranges whose bytes differ as (name, addr, a_bytes, b_bytes)."""
    def __init__(self, a, b, ranges, budget):
        self.a, self.b, self.ranges, self.budget = a, b, ranges, budget
        self.diff = [(n, ranges[n][0], a['fields'][n], b['fields'][n]) for n in ranges if a['fields'][n] != b['fields'][n]]

    @property
    def changed(self):
        return bool(self.diff)

    def report(self):
        out = [f'ab budget {self.budget}: input arm ends at step {self.a["step"]}, control at {self.b["step"]}; '
               f'{len(self.diff)} of {len(self.ranges)} named ranges differ']
        for n, addr, x, y in self.diff:
            out.append(f'  {n} ${addr:x}: input {x.hex()} control {y.hex()}')
        return '\n'.join(out)


# ---- the driver ---------------------------------------------------------------------------------------------------

class Drive:
    def __init__(self, root, dll=None, journal=None, fields=None, period=None, frame=FRAME, record=None, every=500_000,
                 keep=16):
        """root: the M68000 dir (stserver's cwd; the ROM is found from it). journal: path, or None for the default
        location (journalling cannot be turned off). fields: {name: (addr, width)}. period: the game's poll period in
        steps (default: one frame). record: a directory to record each linear stretch into (module docstring,
        "Recordings"), with a checkpoint every `every` steps and `keep` checkpoints in memory."""
        self.root = os.path.abspath(root)
        self.s = StServer(self.root, dll=dll)
        self.fields_map = dict(fields or {})
        self.frame = frame
        self.period = period or frame
        self.step_count = None          # absolute step counter of the machine
        self._gen = 0
        self._cache = []                # [(addr, bytes)] valid for the current generation
        self._pending = 0               # coalesced steps not yet written to the journal
        self._pending_at = None
        self._fork_ids = []
        self.record_root = os.path.abspath(record) if record else None
        self.every, self.keep = every, keep
        self.segments = []
        self._recording = False
        if journal is None:
            journal = os.path.join(os.getcwd(), 'scratchpad', 'stdrive', 'journal',
                                   time.strftime('%Y%m%d-%H%M%S') + f'-{os.getpid()}.jsonl')
        self.journal_path = os.path.abspath(journal)
        os.makedirs(os.path.dirname(self.journal_path), exist_ok=True)
        self._j = open(self.journal_path, 'w')

    # -- journal and raw access --

    def _flush_steps(self):
        if self._pending:
            self._j.write(json.dumps({'op': 'step', 'at': self._pending_at, 'n': self._pending}) + '\n')
            self._pending = 0
            self._pending_at = None

    def _log(self, op, **kw):
        self._flush_steps()
        self._j.write(json.dumps(dict(op=op, at=self.step_count, **kw)) + '\n')

    def note(self, text):
        """A label in the journal (ignored by replay)."""
        self._log('note', text=text)

    def flush(self):
        self._flush_steps()
        self._j.flush()

    def _dirty(self):
        self._gen += 1
        self._cache = []

    def _rec_start(self):
        if not self.record_root:
            return
        seg = os.path.join(self.record_root, f'seg{len(self.segments):03d}')
        self.s('record_start', every=self.every, dir=seg, keep=self.keep)
        self._recording = True
        self.segments.append({'dir': seg, 'base': self.step_count, 'end': None, 'id': None})
        self._log('note', text=f'record_start {seg}')

    def _rec_stop(self):
        if not self._recording:
            return
        self._flush_steps()
        r = self.s('record_stop')
        self._recording = False
        self.segments[-1].update(end=int(r['end']), id=int(r['id']), disk_written=bool(r['disk_written']))
        self._log('note', text=f'record_stop {self.segments[-1]["dir"]} end {r["end"]}')
        with open(os.path.join(self.record_root, 'segments.json'), 'w') as f:
            json.dump(self.segments, f, indent=1)

    def rpc(self, method, **params):
        """Any stserver method that does not change machine state (watches, breakpoints, regs, peek, render, ...)."""
        if method in _STATEFUL:
            raise ValueError(f'{method} changes machine state: use the Drive method so the journal records it')
        return self.s(method, **params)

    def _stepped(self, n, result):
        if n:
            if self._pending == 0:
                self._pending_at = self.step_count
            self._pending += n
        self.step_count = int(result['step'])
        self._dirty()

    # -- machine --

    def load(self, snapshot, disk):
        snapshot = os.path.abspath(snapshot)
        disk = os.path.abspath(disk) if disk else None
        self._rec_stop()
        r = self.s('load', snapshot=snapshot, disk=disk)
        self._dirty()
        self._flush_steps()
        self._j.write(json.dumps({'op': 'load', 'at': None, 'snapshot': snapshot, 'snapshot_sha1': _sha1(snapshot),
                                  'disk': disk, 'disk_sha1': _sha1(disk), 'step': int(r['step'])}) + '\n')
        self.step_count = int(r['step'])
        self._rec_start()
        return r

    def step(self, n):
        """Run exactly n steps (no stop checks)."""
        if n <= 0:
            return
        r = self.s('step', n=n)
        if int(r['steps']) != n:
            raise RuntimeError(f'step {n} ran {r["steps"]}: {r.get("error")}')
        self._stepped(n, r)
        return r

    def run(self, max_steps, until_pc=None, count=None):
        """stserver `run` (breakpoints, stop watches, until_pc); journalled as the steps it ran."""
        kw = {'max_steps': max_steps}
        if until_pc is not None:
            kw['until_pc'] = until_pc
        if count is not None:
            kw['count'] = count
        r = self.s('run', **kw)
        self._stepped(int(r['steps']), r)
        if r['reason'] == 'error':
            raise RuntimeError(f'run: {r.get("error")}')
        return r

    def to_frame(self, phase=0):
        """Step to the next step counter = phase (mod frame); no-op if already there."""
        k = (phase - self.step_count) % self.frame
        self.step(k)
        return k

    def kbd(self, *groups):
        for g in groups:
            self.s('kbd', bytes=[f'{b:02x}' for b in g])
            self._log('kbd', bytes=list(g))
        self._dirty()

    def press(self, inp):
        self.kbd(*inp.press_groups)

    def release(self, inp):
        self.kbd(*inp.release_groups)

    def mouse(self, action, **kw):
        self.s('mouse', action=action, **kw)
        self._log('mouse', action=action, **kw)
        self._dirty()

    def poke(self, addr, width, value):
        self.s('poke', addr=addr, width=width, value=value)
        self._log('poke', addr=addr, width=width, value=value)
        self._dirty()

    def set_reg(self, name, value):
        self.s('set_reg', name=name, value=value)
        self._log('set_reg', name=name, value=value)
        self._dirty()

    def disk(self, path):
        path = os.path.abspath(path) if path else None
        self.s('disk', path=path)
        self._log('disk', path=path, sha1=_sha1(path))
        self._dirty()

    def fork(self):
        r = self.s('fork')
        self._log('fork', id=int(r['id']))
        return int(r['id'])

    def restore(self, fid):
        self._rec_stop()
        r = self.s('restore', id=fid)
        self._log('restore', id=fid)
        self.step_count = int(r['step'])
        self._dirty()
        self._rec_start()

    def drop(self, fid):
        self.s('drop', id=fid)

    def save(self, path):
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.s('save', path=path)
        self._log('save', path=path)
        self.flush()
        return path

    def close(self):
        self._rec_stop()
        self.flush()
        self._j.close()
        try:
            self.s('shutdown')
        except Exception:
            pass
        try:
            self.s.p.stdin.close()
        except Exception:
            pass
        self.s.p.wait()

    # -- memory --

    def read(self, addr, n):
        for a, b in self._cache:
            if a <= addr and addr + n <= a + len(b):
                return b[addr - a:addr - a + n]
        b = self.s.read(addr, n)
        self._cache.append((addr, b))
        return b

    def prefetch(self, addr, n):
        self.read(addr, n)

    def u8(self, addr):
        return self.read(addr, 1)[0]

    def u16(self, addr):
        return int.from_bytes(self.read(addr, 2), 'big')

    def s16(self, addr):
        return int.from_bytes(self.read(addr, 2), 'big', signed=True)

    def u32(self, addr):
        return int.from_bytes(self.read(addr, 4), 'big')

    def field(self, name, signed=False):
        addr, width = self.fields_map[name]
        return int.from_bytes(self.read(addr, width), 'big', signed=signed)

    def fields(self, names=None):
        return {n: self.field(n) for n in (names or self.fields_map)}

    # -- evidence-rule helpers --

    def hold(self, inp, polls=1, period=None, steps=None, align=True, phase=0, release=True, allow_short=False):
        """Press `inp` at the next VBL boundary (align), keep it for `steps` (default polls * period), then release.
        Refuses a hold that does not cover one full poll period unless allow_short. Returns (press_step, release_step)."""
        period = period or self.period
        n = steps if steps is not None else polls * period
        if n < period and not allow_short:
            raise ValueError(f'hold of {n} steps is shorter than the poll period {period}: a sample, not an input')
        if align:
            self.to_frame(phase)
        t0 = self.step_count
        self.press(inp)
        self.step(n)
        if release:
            self.release(inp)
        return t0, self.step_count

    def tap(self, inp, period=None, align=True, gap=True):
        """A press held one poll period plus half a frame, then released for one poll period (gap) so a following tap
        is a new edge."""
        period = period or self.period
        r = self.hold(inp, steps=period + self.frame // 2, period=period, align=align)
        if gap:
            self.step(period)
        return r

    def wait_until(self, addr, value, mask=0xff, width=1, budget=1_000_000):
        """Run until the `width`-byte value at addr satisfies (v & mask) == (value & mask), at most `budget` steps.
        A stop watch on [addr, addr+width) ends each run at any write there and the value is re-read (a write may
        overlap it with other bytes, or write another value), so it is exact to the instruction. Already true: 0 steps."""
        def cur():
            return int.from_bytes(self.read(addr, width), 'big')
        v = cur()
        if (v & mask) == (value & mask):
            return Wait(True, 0, v, 0)
        wid = self.s('watch_add', lo=addr, hi=addr + width - 1, kind='w', stop=True, max_events=1)['id']
        t0, stops = self.step_count, 0
        try:
            while self.step_count - t0 < budget:
                r = self.run(budget - (self.step_count - t0))
                v = cur()
                if r['reason'] != 'watch':
                    break
                stops += 1
                if (v & mask) == (value & mask):
                    return Wait(True, self.step_count - t0, v, stops)
        finally:
            self.s('watch_remove', id=wid)
        return Wait((v & mask) == (value & mask), self.step_count - t0, v, stops)

    def ab(self, fn, budget, ranges=None, control=None, save_dir=None, leave='a'):
        """Same-snapshot, same-budget A/B: fork here, run fn(self) and pad to `budget` steps (the input arm), restore,
        run `control(self)` (default: nothing) padded to the same budget, and read every named range in both.
        ranges: {name: (addr, len)} (default the Drive's fields). save_dir: also save both end snapshots there.
        leave: 'a' or 'b', the end state the machine is left in."""
        ranges = dict(ranges or self.fields_map)
        f0 = self.fork()
        t0 = self.step_count
        ends = {}
        for arm, f in (('a', fn), ('b', control)):
            if arm == 'b':
                self.restore(f0)
            self.note(f'ab arm {arm}')
            if f:
                f(self)
            used = self.step_count - t0
            if used > budget:
                raise ValueError(f'ab arm {arm} ran {used} steps, over the budget {budget}')
            self.step(budget - used)
            e = {'step': self.step_count, 'fields': {n: self.read(a, w) for n, (a, w) in ranges.items()}, 'snap': None}
            if save_dir:
                e['snap'] = self.save(os.path.join(save_dir, f'ab_{arm}.snap'))
            e['fork'] = self.fork()
            ends[arm] = e
        self.restore(ends[leave]['fork'])
        for k in ('a', 'b'):
            self.drop(ends[k]['fork'])
        self.drop(f0)
        return AB(ends['a'], ends['b'], ranges, budget)


# ---- replay -------------------------------------------------------------------------------------------------------

def replay(journal, out_dir, root=None, dll=None):
    """Re-run a journal in a fresh stserver. Each `save` goes to out_dir/<basename> (numbered if a basename repeats).
    Raises if a recorded `at` step does not match or an input file's SHA-1 changed. Returns [(original, replayed)]."""
    with open(journal) as f:
        ops = [json.loads(l) for l in f if l.strip()]
    os.makedirs(out_dir, exist_ok=True)
    root = root or os.getcwd()
    d = Drive(root, dll=dll, journal=os.path.join(out_dir, 'replay.jsonl'))
    fork_map, saves, seen = {}, [], {}
    try:
        for o in ops:
            op = o['op']
            if op not in ('load', 'note') and o['at'] != d.step_count:
                raise RuntimeError(f'replay diverged: {op} recorded at {o["at"]}, machine at {d.step_count}')
            if op == 'load':
                for k in ('snapshot', 'disk'):
                    if o[k] and _sha1(o[k]) != o[k + '_sha1']:
                        raise RuntimeError(f'{k} {o[k]} changed since the journal was written')
                d.load(o['snapshot'], o['disk'])
            elif op == 'step':
                d.step(o['n'])
            elif op == 'kbd':
                d.kbd(o['bytes'])
            elif op == 'mouse':
                d.mouse(o['action'], **{k: v for k, v in o.items() if k not in ('op', 'at', 'action')})
            elif op == 'poke':
                d.poke(o['addr'], o['width'], o['value'])
            elif op == 'set_reg':
                d.set_reg(o['name'], o['value'])
            elif op == 'disk':
                if o['path'] and _sha1(o['path']) != o['sha1']:
                    raise RuntimeError(f'disk {o["path"]} changed since the journal was written')
                d.disk(o['path'])
            elif op == 'fork':
                fork_map[o['id']] = d.fork()
            elif op == 'restore':
                d.restore(fork_map[o['id']])
            elif op == 'save':
                b = os.path.basename(o['path'])
                k = seen.get(b, 0)
                seen[b] = k + 1
                p = os.path.join(out_dir, b if k == 0 else f'{k}_{b}')
                saves.append((o['path'], d.save(p)))
            elif op == 'note':
                d.note(o['text'])
            else:
                raise RuntimeError(f'unknown journal op {op}')
    finally:
        d.close()
    return saves


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='replay a stdrive journal and cmp every saved snapshot with the original')
    ap.add_argument('journal')
    ap.add_argument('out_dir')
    ap.add_argument('--root', default=os.getcwd())
    ap.add_argument('--dll')
    a = ap.parse_args()
    t0 = time.time()
    saves = replay(a.journal, a.out_dir, a.root, a.dll)
    same = 0
    for orig, new in saves:
        eq = os.path.exists(orig) and open(orig, 'rb').read() == open(new, 'rb').read()
        same += eq
        print(('IDENTICAL ' if eq else 'DIFFERENT ') + f'{orig} {new}')
    print(f'{same} of {len(saves)} saved snapshots identical, {time.time() - t0:.1f}s')
