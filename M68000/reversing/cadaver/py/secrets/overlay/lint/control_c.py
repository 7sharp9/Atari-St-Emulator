"""control.py: positive controls for rule c on level 0 (in-memory edits of model.Snap reads, no snapshot written):
door $3b's word set to 999 (no record -> KEY NOT AN OBJECT), to 900+ unused, to key 167 with object 194's MOVE removed (-> listed only in
room 69 outside the closure: NEVER/placed-unreachable), and door $20's word to 155 with 155 hidden (-> NEVER, hidden, no SHOW)."""
import sys, importlib.util, pathlib
sys.argv = sys.argv[:1]
HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('lrc', str(HERE / 'lint_rule_c.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
snap = str(m.ROOT / 'scratchpad/cadaver/gameplay_empire.snap')
import model as M
orig_flags, orig_obj, orig_load = M.Snap.flags, M.Snap.obj, None
def run(label, word=None, hide=None, drop_block=None):
    def flags(self):
        f = orig_flags(self)
        if word is not None: f[0x3b] = dict(f[0x3b], word=word)
        return f
    def obj(self, oid):
        o = orig_obj(self, oid)
        if o and hide == oid: o = dict(o, b3=o['b3'] | 0x80)
        return o
    M.Snap.flags, M.Snap.obj = flags, obj
    ctx = m._load_ctx(0, snap)
    if drop_block: ctx.blocks = [b for b in ctx.blocks if not (b.owner == drop_block[0] and b.event == drop_block[1])]
    fs = m.rule(ctx)
    print('%-34s %s' % (label, [f['detail'][:150] for f in fs if f['owner'] == 'door $3b'] or 'no finding for $3b'))
    M.Snap.flags, M.Snap.obj = orig_flags, orig_obj
run('control: unchanged')
run('word 999 (no record)', word=999)
run('word 167, rat 194 ev5 removed', word=167, drop_block=('obj 194', 5))
run('word 73, 73 hidden', word=73, hide=73)
run('word 472 (lever in room 8, behind $3b)', word=472)
