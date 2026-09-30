"""Sequencer of the music module ($1d6ec init, $1d814 per VBL, $1d9c6 event fetch, command grammar at $1da0a), transcribed to Python at event level:
song table $1f97c (longs) -> song header (3 longs = tracks) -> track = list of longs (pattern addresses; 0 = loop to the first, negative = end)
-> pattern = byte code (note $00-$5f, $60 loop end, $61 loop start n, $62 call long, $63 jump long, $64 transpose, $65 flag, $80-$bf length-$7f,
$c0-$df instrument, $e0 glide (3 bytes), $e1-$ef parameter, $f0-$fe tempo-$ef, $ff pattern end).  A row happens every tempo ($1eb36) VBLs; each channel
whose wait counter ($1f4fe/$1f570/$1f5e2) is 0 fetches until a note and sets wait = length; then every wait is decremented."""
import sys, struct
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
SONGS = 0x1f97c
def s8(v): return v - 256 if v & 0x80 else v

class Chan:
    def __init__(self, ram, track):
        self.m = ram; self.base = track
        self.a2 = self.l(track); self.pos = track + 4
        self.stack = []; self.trans = 0; self.length = 0; self.wait = 0; self.instr = None; self.done = False
        self.param = None; self.loops = 0; self.patterns = set(); self.ended = None
    def l(self, a): return int.from_bytes(self.m[a:a+4], 'big')
    def fetch(self, glob):
        """run commands until a note; returns (raw note, transpose, length, instrument) or None at song end"""
        m = self.m
        while True:
            b = m[self.a2]; self.a2 += 1
            if b <= 0x5f:
                return self.note(b)
            if b == 0xff:
                if self.stack:
                    fr = self.stack.pop()
                    assert fr[0] == 'call', 'pattern end inside a loop frame'
                    self.a2 = fr[1]
                else:
                    v = self.l(self.pos)
                    if v == 0:
                        self.loops += 1
                        self.a2 = self.l(self.base); self.pos = self.base + 4
                    elif v & 0x80000000:
                        self.done = True; return None
                    else:
                        self.a2 = v; self.pos += 4; self.patterns.add(v)
            elif b == 0x61:
                cnt = m[self.a2]; self.a2 += 1; self.stack.append(['loop', self.a2, cnt])
            elif b == 0x60:
                fr = self.stack[-1]; fr[2] -= 1
                if fr[2] > 0: self.a2 = fr[1]
                else: self.stack.pop()
            elif b == 0x62:
                if self.a2 & 1: self.a2 += 1
                tgt = self.l(self.a2); self.a2 += 4
                self.stack.append(['call', self.a2]); self.a2 = tgt
            elif b == 0x63:
                if self.a2 & 1: self.a2 += 1
                self.a2 = self.l(self.a2)
            elif b == 0x64:
                self.trans = s8(m[self.a2]); self.a2 += 1
            elif b == 0x65:
                glob['flag'] = True
            elif b < 0x80: pass
            elif b == 0xe0:
                p, n1, n2 = m[self.a2:self.a2+3]; self.a2 += 3
                return self.note(n2, glide=(p, n1))
            elif b < 0xc0: self.length = b - 0x7f
            elif b < 0xe0: self.instr = b - 0xc0
            elif b < 0xf0: self.param = b - 0xe0
            else: glob['tempo'] = b - 0xef
    def note(self, raw, glide=None):
        self.wait = self.length
        return (raw, self.trans, self.length, self.instr, glide)

def song_tracks(ram, song):
    hdr = int.from_bytes(ram[SONGS + 4*song: SONGS + 4*song + 4], 'big')
    return [int.from_bytes(ram[hdr + 4*c: hdr + 4*c + 4], 'big') for c in range(3)]

def run_song(ram, song, tempo0=6, max_rows=100000, max_events=100000):
    """returns [(row, vbl, channel, raw note, transpose, length, instrument, glide)], ordered as the engine fetches them"""
    ch = [Chan(ram, t) for t in song_tracks(ram, song)]
    glob = {'tempo': tempo0, 'flag': False}
    ev = []; vbl = 0
    for row in range(max_rows):
        for c in range(3):
            if ch[c].done: continue
            if ch[c].wait == 0:
                e = ch[c].fetch(glob)
                if e: ev.append((row, vbl, c) + e)
        if all(c.done for c in ch): break
        for c in ch: c.wait -= 1
        vbl += glob['tempo']
        if len(ev) >= max_events: break
    return ev, ch, glob

if __name__ == '__main__':
    r = ram(WORK + '/data/title_bb7b_0.snap')
    for s in range(3):
        print('song', s, 'tracks', [hex(t) for t in song_tracks(r, s)])
        ev, ch, g = run_song(r, s, max_events=40)
        for e in ev[:12]: print('  ', e)

def song_summary(ram, song):
    """rows and VBLs of one pass through the song (until channel 0's track list wraps or every channel ends), events per channel, distinct patterns, tempo"""
    ch = [Chan(ram, t) for t in song_tracks(ram, song)]
    glob = {'tempo': int.from_bytes(ram[0x1eb36:0x1eb38], 'big'), 'flag': False}
    vbl = 0; row = 0; counts = [0, 0, 0]; tempos = []
    while row < 200000:
        for c in range(3):
            if ch[c].done: continue
            if ch[c].wait == 0:
                e = ch[c].fetch(glob)
                if e: counts[c] += 1
        if all(c.done for c in ch): break
        if any(c.loops for c in ch): break
        for c in ch: c.wait -= 1
        tempos.append(glob['tempo']); vbl += glob['tempo']; row += 1
    return dict(rows=row, vbls=vbl, events=counts, tempos=sorted(set(tempos)), ended=[c.done for c in ch], loops=[c.loops for c in ch],
                patterns=[len(c.patterns) for c in ch])
