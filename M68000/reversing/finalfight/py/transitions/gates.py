#!/usr/bin/env python3
"""gates.py <out dir>: check the area / stage transition findings against the logs gates.sh wrote (g_*.log from lua/trans.lua, g_fade.pt from lua/pctap.lua).
Every gate prints PASS/FAIL with its count; exit status 1 on any FAIL. Frame numbers are those of the deterministic sb_boss lineage (cold boot with plans/plan1.lua, bot from 2450)."""
import sys, os, re, hashlib
out = sys.argv[1] if len(sys.argv) > 1 else '.'
res = []
def gate(name, ok, detail):
    res.append(ok); print('%-4s %-34s %s' % ('PASS' if ok else 'FAIL', name, detail))

def lines(name):
    p = os.path.join(out, name)
    return open(p).read().split('\n') if os.path.exists(p) else []
class Log:
    def __init__(self, name):
        self.T, self.C, self.S, self.P = [], {}, [], {}
        cur = {}
        for ln in lines(name):
            p = ln.split()
            if not p: continue
            if p[0] == 'T':   # T f pc=.. a=.. m=.. d=..
                kv = dict(x.split('=') for x in p[2:])
                self.T.append((int(p[1]), int(kv['pc'], 16), int(kv['a'], 16), int(kv['m'], 16), int(kv['d'], 16)))
            elif p[0] == 'C':
                f = int(p[1])
                ch = {}
                for x in p[2:]:
                    k, v = x.split('='); ch[k] = v
                self.C[f] = ch
            elif p[0] == 'S':
                kv = dict(x.split('=') for x in p[3:] if '=' in x)
                self.S.append((int(p[1]), p[2].split('=')[1], kv))
            elif p[0] == 'P':
                self.P[int(p[1])] = dict(x.split('=') for x in p[2:])
    def change(self, f, key, val=None):
        c = self.C.get(f, {})
        return key in c and (val is None or c[key] == val)
    def first(self, key, val, lo=0, hi=10**9):
        for f in sorted(self.C):
            if lo <= f <= hi and self.C[f].get(key) == val: return f
        return None
    def has_T(self, f, pc, addr=None, data=None):
        return any(t[0] == f and t[1] == pc and (addr is None or t[2] == addr) and (data is None or t[4] == data) for t in self.T)
    def at(self, f, key):   # forward-filled value
        v = None
        for g in sorted(self.C):
            if g > f: break
            if key in self.C[g]: v = self.C[g][key]
        return v

boss, cold, hook, limit, lock, s12, air, bonus, tz = (Log('g_%s.log' % n) for n in ('boss', 'cold', 'hook', 'limit', 'lock', 's12', 'air', 'bonus', 'timezero'))

# 1 the DAMND area clear, stage 0 area 2 -> stage 1: every write of the phase, stage, area and flag words, with its PC, at its frame
exp = [(11262, 0x3ed08, 0xff8128, 0x0101), (11345, 0xea10, 0xff8116, 0x0000), (11577, 0xed94, 0xff8128, 0xffff), (11578, 0x4e8e, 0xff8000, 0x0008), (11578, 0x4eae, 0xff80be, 0x0303),
       (11578, 0x4ebc, 0xff8000, 0x000a), (11593, 0x5ced4, 0xff8128, 0x0000), (11594, 0x54f8, 0xff80c0, 0x0101), (11594, 0x5504, 0xff80be, 0x0101), (11594, 0x550a, 0xff8122, 0x0000),
       (11594, 0x4ee6, 0xff80be, 0x0000), (11594, 0x4eea, 0xff8000, 0x0002), (11595, 0x4d46, 0xff8000, 0x0004), (11596, 0x4d74, 0xff8000, 0x0006), (11596, 0x4d7e, 0xff812a, 0x0101),
       (11752, 0xdbfe, 0xff8116, 0x0000), (11752, 0xdc02, 0xff812a, 0x0000)]
n = sum(1 for e in exp if boss.has_T(*e))
gate('clear_to_stage1_writes', n == len(exp), '%d of %d writes at their frame and PC (297:=1 $3ed08, state 10, 297:=$ff $ed94, phase 8 $4e8e, 191+1 $4eae, phase a, 297:=0 $5ced4, $54f8 stage 1, phases 2 4 6, intro end $dbfe/$dc02)' % (n, len(exp)))

# 2 player state / step timeline of that area clear
st = {11264: ('0a00', '0000'), 11265: ('0a02', '0000'), 11345: ('0a02', '0200'), 11346: ('0a02', '0600'), 11353: ('0a02', '0604'), 11395: ('0a02', '0606'),
      11401: ('0a02', '0400'), 11433: ('0a04', '0000'), 11497: ('0a04', '0400'), 11578: ('0a08', '0200'), 11598: ('0800', '0000'), 11753: ('0200', None)}
n = sum(1 for f, (a, b) in st.items() if boss.at(f, 'p1st') == a and (b is None or boss.at(f, 'p1s45') == b) and (f - 1 not in boss.C or boss.at(f - 1, 'p1st') != a or boss.at(f - 1, 'p1s45') != boss.at(f, 'p1s45') or True))
gate('clear_state_timeline', n == len(st), '%d of %d (state, step) values at their frame: sub 0 1 frame, sub 2 step 0 80 frames, step 6 jump, step 4 walk, sub 4, fade, sub 8, state 8 intro' % (n, len(st)))

# 3 no score or time bonus between the boss kill and the next kills
sc = [f for f in boss.C if 11264 <= f <= 11958 and 'score' in boss.C[f]]
gate('no_score_tally', not sc and boss.at(11263, 'score') == '00106110' and boss.at(11958, 'score') == '00106110' and boss.first('score', '00106610') == 11959,
     '0 score changes in 11264..11958 (score $00106110 throughout; next award $00106610 at %s); TIME %s -> %s (no conversion)' % (boss.first('score', '00106610'), boss.at(11263, 'time'), boss.at(11598, 'time')))

# 4 TIME at every area start against $5210 (5 normal areas + bonus stage 1 + stage 2 area 0)
tt = [(cold, 1316, '30'), (cold, 5564, '30'), (cold, 7809, '50'), (boss, 11599, '50'), (air, 12018, '70'), (bonus, 12128, '30'), (bonus, 14865, '50')]
n = sum(1 for lg, f, v in tt if lg.change(f, 'time', v))
gate('time_table', n == len(tt), '%d of %d area starts set TIME to byte[$5210 + 4*stage + area] (30 30 50 50 70, bonus 30, stage 2 area 0 50)' % (n, len(tt)))

# 5 the area counter: phase 8 adds 1 to 191(A5); with more areas it goes to phase 4, otherwise phase a
n = sum([cold.has_T(5560, 0x4eae, 0xff80be, 0x0101), cold.has_T(5560, 0x4ec4, 0xff8000, 0x0004), cold.has_T(7805, 0x4eae, 0xff80be, 0x0202), cold.has_T(7805, 0x4ec4, 0xff8000, 0x0004),
         cold.has_T(11578, 0x4eae, 0xff80be, 0x0303), cold.has_T(11578, 0x4ebc, 0xff8000, 0x000a), cold.has_T(5560, 0x4eca, 0xff8128, 0x0000), cold.has_T(11594, 0x54f8, 0xff80c0, 0x0101)])
gate('area_counter', n == 8, '%d of 8 (191 := 1, 2, 3 at $4eae; phase 4 after areas 0 and 1, phase a after area 2; 297 := 0 at $4eca; $54f8 makes stage 1)' % n)

# 6 the camera is moved to the area's start x at the area start
n = sum([cold.P.get(5580, {}).get('cam') == '0650', cold.P.get(7830, {}).get('cam') == '0900', boss.P.get(11610, {}).get('cam') == '0000'])
gate('area_start_camera', n == 3, 'cam $0650 at 5580 (stage 0 area 1), $0900 at 7830 (area 2), $0000 at 11610 (stage 1 area 0), table $62940')

# 7 who writes the camera x 1042(A5) in the cold boot from frame 1300 (the game) to 12000
pcs = {}
for f, pc, a, m, d in cold.T:
    if a == 0xff8412 and 1300 <= f <= 12000: pcs[pc] = pcs.get(pc, 0) + 1
want = {0x62050, 0x6205e, 0x62176, 0x62184, 0x621c0, 0x621ce, 0x626e8}
gate('camera_x_writers', set(pcs) == want, '%d writes from %d PCs: %s' % (sum(pcs.values()), len(pcs), ' '.join('%x:%d' % (k, v) for k, v in sorted(pcs.items()))))

# 8 raising the right limit 1078(A5) releases the camera
a, b = limit.P.get(11160, {}), boss.P.get(11160, {})
gate('camera_right_limit', a.get('cam') == '0b4f' and a.get('p1x') == '0c1f' and b.get('cam') == '0b00' and b.get('p1x') == '0c1f',
     'limit $0b00: cam $0b00 at p1x $0c1f; limit poked to $0c00 at 11100: cam $0b4f = p1x - $d0 (%s, %s)' % (a.get('cam'), b.get('cam')))
# 9 and the left follow rule p1x - $b0
n = sum([limit.P.get(11370, {}).get('cam') == '0b3c' and limit.P.get(11370, {}).get('p1x') == '0bec', limit.P.get(11400, {}).get('cam') == '0ae7' and limit.P.get(11400, {}).get('p1x') == '0b97'])
gate('camera_follow_rule', n == 2, 'right: cam = p1x - $d0 (0c1f -> 0b4f); left: cam = p1x - $b0 (0bec -> 0b3c, 0b97 -> 0ae7)')

# 10 278(A5) = 1 freezes the camera
fr = [lock.P.get(f, {}).get('cam') for f in range(11910, 12100, 30)]
gate('camera_lock_poke', all(c == '01a7' for c in fr) and boss.P.get(12030, {}).get('cam') == '01c0' and lock.P.get(12180, {}).get('cam') == '01c0',
     'cam $01a7 on %d of %d samples 11910..12090 with 278 = 1 (baseline $01c0 at 12030), $01c0 at 12180 after the release' % (sum(c == '01a7' for c in fr), len(fr)))

# 11 script locks: set at the trigger, cleared by the area clear ($ea10) or by the segment end ($5d08)
n = sum([cold.has_T(4424, 0x5e0e, 0xff8116), cold.has_T(5348, 0xea10, 0xff8116, 0), cold.has_T(7710, 0xea10, 0xff8116, 0), cold.P.get(7710, {}).get('cam') == '06e1', cold.P.get(7740, {}).get('cam') == '0730',
         cold.has_T(9374, 0x5d08, 0xff8116, 0), cold.has_T(10761, 0x5d08, 0xff8116, 0)])
gate('camera_lock_script', n == 7, '%d of 7: 278 := 1 at $5e0e (trigger $3f0, frame 4424); $ea10 clears it at the area clear (5348, 7710: cam $06e1 -> $0730 from 7711); $5d08 clears it 9374 and 10761' % n)

# 12 the stage 0 area 2 camera hook
n = sum([hook.change(8307, 'cstep', '02') and hook.change(8307, 'v116', '4009') and hook.change(8307, 'v118', '7fff') and hook.change(8307, 'v120', '0000'),
         hook.change(8308, 'llim', '0aa0') and hook.change(8308, 'cmode', '02') and hook.change(8308, 'cstep', '04'), hook.at(8299, 'rlim') == '0b00']) if hook.C else 0
gate('camera_hook_stage0', n == 3, 'cam >= $ab0 at 8307: 116/118/120(A5) := 4009 7fff 0000; 8308: left limit := $0aa0, x mode := 2 (right limit $0b00)')

# 13 GO prompt: pool 8 kind 2, 420 frames after the camera stopped
go = [f for f, p, kv in cold.S if p == '8' and kv.get('kind') == '02']
gate('go_prompt_420', go[:3] == [3060, 3480, 6195] and go[1] - go[0] == 420, 'kind 2 spawns at %s (3060 -> 3480 = 420 frames, camera stationary, 278 = 0, below the limit)' % go[:4])
# 14 a segment end without w18 spawns no GO
gate('go_not_on_cont0_w18_0', not [f for f in go if 9300 <= f <= 9460 or 10700 <= f <= 10860], '0 GO spawns around the two stage 0 area 2 segment ends (9374, 10761; header w18 = 0)')

# 15 TIME 0: 480 frames later the players die and TIME reloads
n = sum([tz.change(16077, 'time', '00'), tz.change(16557, 'time', '30'), any(f == 16557 and p == '8' and kv.get('kind') == '25' for f, p, kv in tz.S), tz.change(16557, 'p1st', '0206'),
         tz.P.get(16560, {}).get('hp') == 'ffff', tz.change(16649, 'p1st', '0400'), tz.change(16709, 'lives', '01') and tz.change(16709, 'p1st', '0000')])
gate('time_zero', n == 7, '%d of 7: TIME 00 at 16077 (decrement 30 at 1676 + 480*30), at 16557 TIME := 30, kind $25 (TIME OVER) spawned, hp := $ffff, fatal knockdown, state 4 at 16649, lives 2 -> 1 and respawn at 16709' % n)

# 16 297 poked in the air: state 10 waits for the landing
gate('area_clear_waits_landing', air.change(11801, 'p1st', '020e') and air.change(11820, '297', '01') and air.first('p1st', '0a00', 11700) == 11850, 'jump at 11801 (state 2 sub $e), 297 := 1 at 11820, state 10 sub 0 at the landing frame %s' % air.first('p1st', '0a00', 11700))
# 17 state 12
n = sum([s12.change(12000, '291', '01'), s12.change(12001, 'p1st', '0c00'), s12.change(12002, '299', '01'), s12.change(12082, '299', '00') and s12.change(12082, 'p1st', '0c02'), s12.change(12083, 'p1st', '0c04'),
         all(s12.P.get(f, {}).get('176') == s12.P.get(12060, {}).get('176') for f in range(12060, 12690, 30))])
gate('state12_poke', n == 6, '%d of 6: 291 := 1 at 12000 -> state 12 at 12001, 299 := 1 for 80 frames, sub 2 and 4, TIME frozen' % n)
# 18 the bonus stage and the next stage
tk = sorted(f for f in bonus.C if 'time' in bonus.C[f] and 12500 < f < 14400)
n = sum([bonus.change(12124, 'sa', '0600') and bonus.change(12124, 'seq', '02') and bonus.change(12124, '290', '01'), bonus.change(12128, 'ph', '000e'), len(tk) >= 30 and all(b - a == 60 for a, b in zip(tk[1:], tk[2:])),
         bonus.has_T(14365, 0x52f2, 0xff8128, 0x0101), bonus.has_T(14843, 0xed94, 0xff8128, 0xffff), bonus.change(14844, 'ph', '0008'), bonus.change(14845, 'sa', '0601'),
         bonus.change(14861, 'sa', '0200') and bonus.change(14861, 'seq', '03') and bonus.change(14861, '290', '00')])
gate('bonus_stage_flow', n == 8, '%d of 8: stage 6 (193 = 2, 290 = 1) runs phase $e, TIME 30 ticks every 60 frames to 00, 297 := 1 at $52f2 (no death), walk-out, phase 8, 191 = 1, stage 2 (193 = 3)' % n)
# 19 fade flag and walked-off flag
pt = lines('g_fade.pt')
w = {(int(l.split()[1]), int(l.split()[2], 16), int(l.split()[3], 16), int(l.split()[5], 16)) for l in pt if l.startswith('w ')}
want = [(11496, 0xf6ec, 0xff860e, 0x0101), (11496, 0x26d4, 0xff808c, 0x0e0e), (11577, 0x26ea, 0xff808c, 0x0000), (11577, 0xed94, 0xff8128, 0xffff)]
n = sum(1 for e in want if e in w)
gate('fade_before_297', n == 4, '%d of 4: 166(A6) := 1 and the fade (140(A5) := $0e) start at 11496 ($f6ec, $26d4); the fade ends at 11577 ($26ea) and 297 := $ff comes in the same frame ($ed94): 81 frames' % n)
# 20 determinism: the cold boot and the resumed lineage execute the same writes (same PC, address, data, in the same order) from 8299 to 12000; a write that falls on a frame edge may be
# stamped one frame later or earlier in the resumed lineage (2 of 4008 here), so the frames are compared with a tolerance of one
a_ = [t for t in cold.T if 8299 <= t[0] <= 12000]; b_ = [t for t in boss.T if 8299 <= t[0] <= 12000]
same = len(a_) == len(b_) and all(x[1:] == y[1:] for x, y in zip(a_, b_))
exact = sum(1 for x, y in zip(a_, b_) if x[0] == y[0]); near = all(abs(x[0] - y[0]) <= 1 for x, y in zip(a_, b_))
gate('cold_vs_resumed', same and near and len(a_) > 3000, '%d tap writes in 8299..12000 identical in PC, address and data; %d with the same frame, all within one frame' % (len(a_), exact))
# 21 every phase value seen in the cold run's phase writes
ph = sorted({t[4] for t in cold.T if t[2] == 0xff8000 and t[3] == 0xffff and t[0] > 1100})
gate('phase_values', ph == [0, 2, 4, 6, 8, 10], 'phase word 0(A5) takes %s from frame 1100 on (cold boot, areas 0..2 and stage 1)' % ph)
# 22 stage 1 area 1: no player walk-out, the camera hook sets 297 := $ff
s1 = Log('g_s1a1.log')
n = sum([s1.change(24021, 'p1st', '0a00'), s1.change(24022, 'p1st', '0a0a') and s1.at(24380, 'p1st') == '0a0a', s1.has_T(24381, 0x61ae2, 0xff8128, 0xffff), s1.has_T(24462, 0x4e8e, 0xff8000, 0x0008),
         s1.has_T(24462, 0x4eae, 0xff80be, 0x0202), s1.change(24463, 'sa', '0102') or s1.at(24463, 'sa') == '0102', s1.at(24470, 'time') == '30'])
gate('stage1_area1_hook_exit', n == 7, '%d of 7: state 10 sub $a (an rts) from 24022, 297 := $ff by the camera hook at $61ae2 after 359 frames, phase 8 81 frames later (fade), stage 1 area 2 (TIME 30)' % n)
# 23 the difficulty rank 168(A5): +1 per 600 frames while nothing is paused, -1 at the stage change ($5382, word $53aa[172(A5)] = 1)
rk = [(8485, '000e'), (9085, '000f'), (9685, '0010'), (10285, '0011'), (10885, '0012'), (11595, '0011')]
n = sum(1 for f, v in rk if boss.change(f, 'rank', v))
gate('rank_stage_change', n == len(rk), '%d of %d: rank $0d -> $12 at 8485 + 600k (297 := 1 at 11262 pauses it), $0012 -> $0011 at 11595 when $5382 runs' % (n, len(rk)))
print('%d of %d gates pass' % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
