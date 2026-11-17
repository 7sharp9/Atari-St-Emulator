"""Python model of Little Computer People's behaviour scheduler (ST, Mockingbird #3 build; README "The behaviour
scheduler"). Transcribed from the routines' 68000 bodies, not from a decompile:

  `$1876a` rnd(lo, hi): lo + (XBIOS 17 Random() & $7fff) mod (hi - lo + 1)
  `$1747e` secondary desire: hours awake -> period (begin/middle/end) -> list A/B/C by personality, weekday
           override, then draw from the 16-entry list until the draw differs from the last action `$4c5a4`.

TOS 1.00's Random (the emulator runs the real ROM): seed = seed * 3141592621 + 1 (mod 2^32), returns
(seed >> 8) & $ffffff; seed is the long at `$29b8`.
"""
SEED = 0x29b8
LIST_A, LIST_B, LIST_C, PERIOD_TABLE = 0x2b43e, 0x2b45e, 0x2b47e, 0x2b49e

# name -> (address, width) of the inputs `$1747e` reads
FIELDS = {
    'hour': (0x4ca20, 2),         # current hour, 0..23
    'mday': (0x4ca22, 2),         # day of the month (read by the weekday routine $2459c)
    'wake': (0x5142c, 2),         # HYBER +$06, wake-up hour
    'personality': (0x51434, 2),  # HYBER +$0e, 0..7
    'ill': (0x5145a, 2),          # HYBER +$34, illness level
    'in_bed': (0x51460, 2),       # HYBER +$3a
    'last': (0x4c5a4, 2),         # the action most recently started (written by $172a6)
}

BROKEN = ['no_weekday', 'no_norepeat', 'period_hours', 'ill_ge1', 'rnd_0_14', 'transposed']


def tos_random(seed):
    seed = (seed * 3141592621 + 1) & 0xffffffff
    return seed, (seed >> 8) & 0xffffff


def rnd(seed, lo, hi):
    seed, r = tos_random(seed)
    return seed, lo + (r & 0x7fff) % (hi - lo + 1)


def read_tables(read):
    def words(a, n):
        b = read(a, 2 * n)
        return [int.from_bytes(b[2 * i:2 * i + 2], 'big', signed=True) for i in range(n)]
    return {'A': words(LIST_A, 16), 'B': words(LIST_B, 16), 'C': words(LIST_C, 16),
            'period': words(PERIOD_TABLE, 24)}


def secondary(st, t, variant='true'):
    """Return (action, list name) as `$1747e` would. `variant` names one deliberately wrong rule (a control)."""
    awake = st['hour'] - st['wake']
    if awake < 0:
        awake += 24
    ill_limit = 1 if variant == 'ill_ge1' else 2
    if awake >= 18 or st['ill'] >= ill_limit:
        return (4 if st['in_bed'] == 0 else -1), 'bed'
    period = awake % 3 if variant == 'period_hours' else (awake // 2) % 3
    if variant == 'transposed':
        idx = st['personality'] % 3 * 8 + period          # wrong axis order
    else:
        idx = period * 8 + st['personality']
    which = 'ABC'[t['period'][idx]]
    if variant != 'no_weekday' and which == 'A':
        if st['weekday'] == 0:
            which = 'C'
        elif st['weekday'] == 6:
            which = 'B'
    seed = st['seed']
    hi = 14 if variant == 'rnd_0_14' else 15
    for _ in range(1000):
        seed, k = rnd(seed, 0, hi)
        a = t[which][k]
        if variant == 'no_norepeat' or a != st['last']:
            return a, which
    return None, which


# ---- `$16f50`, the top-level chooser, run whenever the LCP is idle ------------------------------------------
TOP = {  # name -> address of the word `$16f50` reads (all words)
    'event_head': 0x2c948,   # -1 when the house-event queue is empty, else `$27270` dequeues and `$1721c` runs it
    'alarm': 0x3df6c,        # alarm clock ringing
    'pee': 0x51470,          # HYBER +$4a, needs to pee
    'ill': 0x5145a, 'thirst': 0x51464, 'water': 0x5141a, 'hunger': 0x5146a,
    'bits': 0x5147e,         # HYBER +$58; bits 9..11 = cans of food
    'last': 0x4c5a4, 'hour': 0x4ca20,
    'lunch_done': 0x2ae18, 'dinner_done': 0x2ae1a, 'wake_done': 0x2ae1c, 'sleep_done': 0x2ae1e,
    'lunch': 0x5142e, 'dinner': 0x51430, 'wake': 0x5142c, 'sleep': 0x5142a,
    'qcount': 0x3dce2,
}
QPRIO, QACT = 0x3e272, 0x40966   # ten words each: the player-query queue (priority, action)


def toplevel(st, variant='true'):
    """Return (label, action, qcount, qprio, qact) for one `$16f50` pass. label: 'event', 'start' (an action handed
    to `$172a6`), 'agree' (`$2310a`, before a play/piano query runs) or 'secondary' (`$1747e` reached)."""
    q = st['qcount']; qp = list(st['qprio']); qa = list(st['qact'])
    if st['event_head'] != -1:
        return 'event', None, q, qp, qa
    if st['alarm']:
        return 'start', 0x29, q, qp, qa
    if st['pee']:
        return 'start', 0x15, q, qp, qa
    seed = st['seed']
    a = 0 if st['ill'] > 0 else 0x42
    if st['thirst'] > 0:
        seed, r = rnd(seed, 1, 100)
        if r > a and (st['ill'] == 0 or st['water'] != 0 or variant == 'ill_ignores_water'):
            return 'start', 0x0d, q, qp, qa
    cans = (st['bits'] >> 9) & 7
    if st['hunger'] > 0:
        seed, r = rnd(seed, 1, 100)
        if r > a:
            if (st['ill'] != 0 and cans != 0) or ((st['last'] != 0x12 or variant == 'eat_repeats') and st['ill'] == 0):
                return 'start', 0x12, q, qp, qa
    for done, hour, act in (('lunch_done', 'lunch', 0x19), ('dinner_done', 'dinner', 0x19),
                            ('wake_done', 'wake', 0x2b), ('sleep_done', 'sleep', 0x2c)):
        if st[done] == 0 and st[hour] == st['hour']:
            return 'start', act, q, qp, qa
    if q > 0:
        if qp[0] < 4:
            qa[:9] = qa[1:10]; qp[:9] = qp[1:10]
            if variant == 'drop_decrements':
                q -= 1
        elif qp[0] < (7 if variant == 'execute_at_7' else 8):
            qp[0] += 1
        else:
            act = qa[0]
            if act in (0x10, 0x1a):   # `$2310a` runs before the shift, so a stop there sees the queue unchanged
                return 'agree', act, q, qp, qa
            qa[:9] = qa[1:10]; qp[:9] = qp[1:10]
            q -= 1
            return ('agree' if act in (0x10, 0x1a) else 'start'), act, q, qp, qa
    return 'secondary', None, q, qp, qa


# ---- `$17c46`, a new LCP (run when there is no HYBER file) ---------------------------------------------------
# (field, HYBER offset or absolute address, lo, hi), in the order the routine draws them
NEW_DRAWS = [('head', 0x51480, 2, 6), ('name_index', None, 0, 265),
             ('clothes', 0x51426, 0, 15), ('pyjamas', 0x51428, 0, 7), ('sleep', 0x5142a, 22, 24),
             ('lunch', 0x5142e, 11, 13), ('dinner', 0x51430, 17, 19), ('unused', 0x51432, 0, 3),
             ('personality', 0x51434, 0, 7), ('happy_t0', 0x51450, 6, 24), ('happy_t1', 0x51452, 6, 24),
             ('happy_t2', 0x51454, 6, 12), ('tidiness', 0x51462, 20, 80), ('thirst_t', 0x51466, 45, 75),
             ('hunger_t', 0x5146c, 75, 120), ('pee_t', 0x51472, 20, 40)]


def new_person(seed, names, variant='true'):
    """names: the NAMES file bytes (266 entries of 10). Returns {field: value} plus 'wake' and 'name'."""
    draws = NEW_DRAWS
    if variant == 'swap_unused_personality':
        draws = draws[:7] + [draws[8], draws[7]] + draws[9:]
    out = {}
    for name, _, lo, hi in draws:
        if variant == 'sleep_22_23' and name == 'sleep':
            hi = 23
        seed, out[name] = rnd(seed, lo, hi)
    if out['sleep'] > 23:
        out['sleep'] -= 24
    out['wake'] = out['sleep'] + 6 if out['sleep'] + 6 <= 23 else out['sleep'] - 18
    raw = names[out['name_index'] * 10: out['name_index'] * 10 + 10]
    out['name'] = bytes(c if c >= 0x41 else 0 for c in raw)
    return out


# ---- `$24648`, the clock and needs tick, run once per game frame by the frame wait `$26914` -------------------
# A frame is at least 25 ticks of the 200 Hz clock and 2 VBLs apart (`$263a6`), so at most 8 frames a second;
# `$24648` acts on every 8th frame (frame counter `$51424` & 7 == 0): 60 of those make a game minute, 60 minutes an hour.
TICK = {  # name -> address of each word `$24648` (and `$2489e`, `$17f0c`, `$24a04`) reads or writes
    'frame': 0x51424, 'sec': 0x4c592, 'min': 0x55102, 'hour': 0x4ca20,
    'mday': 0x4ca22, 'month': 0x3dcd0, 'year': 0x4097c,          # day and month zero-based; year 86 = 1986
    'thirst': 0x51464, 'thirst_len': 0x51466, 'thirst_left': 0x51468,
    'hunger': 0x5146a, 'hunger_len': 0x5146c, 'hunger_left': 0x5146e,
    'pee': 0x51470, 'pee_left': 0x51474,
    'ill': 0x5145a, 'ill_left': 0x5145c, 'ill_dir': 0x5145e,
    'happy': 0x5144e, 'happy_t0': 0x51450, 'happy_t1': 0x51452, 'happy_t2': 0x51454,
    'happy_left': 0x51456, 'happy_dir': 0x51458,
    'event_block': 0x2ae16, 'away': 0x51418, 'event_flag': 0x2ae12,
    'lunch_done': 0x2ae18, 'dinner_done': 0x2ae1a, 'wake_done': 0x2ae1c, 'sleep_done': 0x2ae1e,
}
MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]   # table at `$2c7b8`, read from RAM
TICK_BROKEN = ['no_illness_restart', 'event_1_100', 'happy_runs_when_ill', 'no_leap', 'ill_capped_2']


def _w(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


EVQ = 0x2c948    # ten words, -1 = free; `$16f50` rule 1 takes the head


def enqueue_event(q, ev, away):
    """`$27222`: put `ev` in the first free slot, unless he is away or the last slot is taken."""
    q = list(q)
    if away == 0 and q[9] == -1:
        q[q.index(-1)] = ev
    return q


def needs_tick(st, variant='true'):
    """One call of `$24648` on state dict `st` (TICK names plus 'seed'); returns the new dict.
    Every value is a signed word, as the routine compares them."""
    s = dict(st)

    def starve():                                    # `$2489e`: a need already at 3 runs out again
        if variant == 'no_illness_restart' and s['ill'] > 0:
            return
        s['ill'] = 1; s['ill_left'] = 60; s['ill_dir'] = 1; s['happy_dir'] = 1
        if s['happy'] < 2:
            s['happy'] += 1

    if s['frame'] & 7:
        return s
    s['sec'] = _w(s['sec'] + 1)
    if s['sec'] != 60:
        return s
    s['sec'] = 0
    for need, ln, left in (('thirst', 'thirst_len', 'thirst_left'), ('hunger', 'hunger_len', 'hunger_left')):
        s[left] = _w(s[left] - 1)
        if s[left] < 1:
            s[left] = s[ln]
            if s[need] < 3:
                s[need] += 1
            else:
                starve()
    if s['ill'] > 0:
        s['ill_left'] = _w(s['ill_left'] - 1)
        if s['ill_left'] == 0:
            s['ill'] = _w(s['ill'] + s['ill_dir'])
            if variant == 'ill_capped_2' and s['ill'] > 2:
                s['ill'] = 2
            if s['ill'] >= 2:
                s['happy'] = 2
            s['ill_left'] = 5 if s['ill_dir'] == -1 else 60
    s['pee_left'] = _w(s['pee_left'] - 1)
    if s['pee_left'] < 1:
        s['pee_left'] = 9999; s['pee'] = 1
    if 7 < s['hour'] < 22:
        lo, hi = (1, 100) if variant == 'event_1_100' else (0, 100)
        s['seed'], r = rnd(s['seed'], lo, hi)
        if r < 2 and s['event_block'] == 0 and s['away'] == 0:
            s['event_flag'] = 1
            s['evq'] = enqueue_event(s['evq'], 0x1e, s['away'])
    s['min'] = _w(s['min'] + 1)
    if s['min'] != 60:
        return s
    s['min'] = 0
    if (s['ill'] == 0 or s['happy'] != 2 or variant == 'happy_runs_when_ill'):
        s['happy_left'] = _w(s['happy_left'] - 1)
        if s['happy_left'] == 0:
            s['happy'] = _w(s['happy'] + s['happy_dir'])
            if s['happy'] < 1:
                s['happy'] = 0; s['happy_dir'] = 1
            elif s['happy'] >= 2:
                s['happy'] = 2; s['happy_dir'] = -1
            s['happy_left'] = s[('happy_t0', 'happy_t1', 'happy_t2')[s['happy']]]
    s['hour'] = _w(s['hour'] + 1)
    if s['hour'] != 24:
        return s
    s['hour'] = 0
    for k in ('lunch_done', 'dinner_done', 'wake_done', 'sleep_done'):    # `$17f0c`
        s[k] = 0
    if s['month'] == 1 and variant != 'no_leap':
        days = 29 if s['year'] % 4 == 0 else 28
    else:
        days = MONTH_DAYS[s['month']]
    s['mday'] = _w(s['mday'] + 1)
    if s['mday'] == days:
        s['mday'] = 0
        s['month'] = _w(s['month'] + 1)
        if s['month'] == 12:
            s['month'] = 0; s['year'] = _w(s['year'] + 1)
    return s
