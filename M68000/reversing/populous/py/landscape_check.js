'use strict';
// landscape_check.js <in.json> <out.json>: runs landscape_core.js on the test list written by
// landscape_infographic.py --check and writes the resulting states. No judgement here: the
// Python side compares against popgen.py / powers_ref.py / pop_render.py.
const fs = require('fs');
const path = require('path');
const LS = require(path.join(__dirname, 'landscape_core.js'));

const inp = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const data = inp.data;
const blocks = data.lands.map(l => l.blocks.map(LS.decodeImg));
const spr = { 76: LS.decodeImg(data.spr76), 77: LS.decodeImg(data.spr77) };

function worldFrom(st) {
  const w = new LS.World(st.seed);
  w.h.set(st.h); w.alt.set(st.alt); w.shape.set(st.shape); w.feat.set(st.feat);
  return w;
}
function stateOf(w) {
  return { seed: w.seed, h: Array.from(w.h), alt: Array.from(w.alt), shape: Array.from(w.shape), feat: Array.from(w.feat) };
}

const out = inp.tests.map(t => {
  if (t.kind === 'gen') {
    const w = LS.genWorld(t.seed, t.pre, null);
    return stateOf(w);
  }
  if (t.kind === 'genrec') {           // replay record: the log must rebuild the same heights
    const rec = { steps: [], log: [], clusters: [] };
    const w = LS.genWorld(t.seed, t.pre, rec);
    const r = LS.replayWorld(rec, rec.steps.length + rec.clusters.length);
    const same = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
    const mid = LS.replayWorld(rec, rec.steps.length);          // before the scatter
    return { h: Array.from(w.h), replay: Array.from(r.h), nlog: rec.log.length,
             lastCum: rec.steps[rec.steps.length - 1].cum, ncl: rec.clusters.length,
             full: same(r.alt, w.alt) && same(r.shape, w.shape) && same(r.feat, w.feat),
             noScatter: mid.feat.every(v => v === 0) && mid.shape.every(v => v !== 0x2f) };
  }
  if (t.kind === 'cmd') {
    const w = worldFrom(t.state);
    const r = t.op === 'raise' ? LS.cmdRaise(w, t.x, t.y) : LS.cmdLower(w, t.x, t.y);
    const s = stateOf(w); s.points = r.points; s.cost = r.cost; return s;
  }
  if (t.kind === 'power') {
    const w = worldFrom(t.state);
    const d0 = w.draws;
    if (t.op === 'flood') LS.flood(w);
    else if (t.op === 'eq') LS.earthquake(w, t.x, t.y);
    else if (t.op === 'volcano') LS.volcano(w, t.x, t.y);
    else if (t.op === 'swamp') LS.swamp(w, t.x, t.y, null);
    const s = stateOf(w); s.draws = w.draws - d0; return s;
  }
  if (t.kind === 'render') {
    const w = worldFrom(t.state);
    const pix = new Uint8Array(64000).fill(LS.EMPTY);
    LS.renderTerrain(pix, w, blocks[t.land], spr, t.cx, t.cy, t.shim, {});
    return { pix: Buffer.from(pix).toString('hex') };
  }
  if (t.kind === 'corner') {
    const w = worldFrom(t.state);
    return { res: t.pts.map(p => LS.cornerAt(w, t.ox, t.oy, p[0], p[1])) };
  }
  throw new Error('unknown test kind ' + t.kind);
});
fs.writeFileSync(process.argv[3], JSON.stringify(out));
