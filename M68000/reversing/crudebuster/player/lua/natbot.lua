-- natbot.lua: play Crude Buster level CB_LEVEL (0..5) from startlevel's entry to the level-cleared flag with no RAM pokes except the
--   health cell (CB_GOD=1) and the level byte at the game-start write ($146e, as startlevel.lua). Moves beyond bot.lua: grab (b3) a liftable
--   pool B prop and throw it at a lock wall (pool B types 24, 28, 29, 30) or an enemy; grab and throw a pool A enemy; watchdog wiggle.
--   Positions: x = word at +8, y = word at +12 of a record; facing byte +7 (0 right).
-- env: CB_DIR (reversing/crudebuster/lua)  CB_LEVEL  CB_STOP (last frame, default 40000)  CB_OUT (dir: nat.csv, events.txt)  CB_LOG (frames per csv row, default 30)
--   CB_GOD (1: health $80113 = $38 every frame)  CB_SAVEAT "frame:name,..."  CB_LOAD (state name; policy resumes at once)  CB_SHOTS "lo:hi:step"
--   CB_SAVEON "start,boss,clear": save a state when the level starts being playable (name nb_start), when a pool A record with +6... is not used; boss = first
--   frame the lock bit $80400.5 is set with the scroll at a lock cell (nb_lock<n>), clear = the level-cleared flag $80040.4 (nb_clear)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local stop = tonumber(os.getenv("CB_STOP") or "40000")
local logn = tonumber(os.getenv("CB_LOG") or "30")
local god = (os.getenv("CB_GOD") or "1") == "1"
local keeptimer = os.getenv("CB_TIMER") == "1" -- 1: refill the level timer ($80042, BCD) when it drops below $100 (the timer kills the player at 0 even in god mode)
local out = os.getenv("CB_OUT") or "."
local saveat = {}
for f, n in (os.getenv("CB_SAVEAT") or ""):gmatch("(%d+):([%w_]+)") do saveat[tonumber(f)] = n end
local slo, shi, sst = 0, -1, 1
if os.getenv("CB_SHOTS") then slo, shi, sst = os.getenv("CB_SHOTS"):match("(%d+):(%d+):(%d+)"); slo, shi, sst = tonumber(slo), tonumber(shi), tonumber(sst) end
local cpu = manager.machine.devices[":maincpu"]
local m = L.mem
taps = {}
taps[1] = m:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return ((want << 8) | want) end
end)
local csv = io.open(out .. "/nat.csv", "w")
csv:write("frame,px,py,face,act,sub,hold,hp,lives,score,scrollx,scrolly,nenemy,lvl,flags40,flags400,mode\n")
local ev = io.open(out .. "/events.txt", "w")
local function log(f, s) ev:write(string.format("%d %s\n", f, s)); ev:flush() end

local LOCK = { [24] = true, [28] = true, [29] = true, [30] = true }
local LIFT = { [6] = true, [7] = true, [8] = true, [9] = true, [10] = true, [11] = true, [12] = true, [13] = true, [14] = true, [15] = true, [16] = true, [17] = true, [36] = true, [37] = true, [44] = true, [63] = true, [64] = true, [66] = true, [67] = true, [68] = true }
local HINT = { [8] = true, [9] = true, [10] = true, [36] = true, [37] = true, [44] = true }
local function pool(base, stride, n)
  local t = {}
  for i = 0, n - 1 do
    local a = base + i * stride
    local b0 = m:read_u8(a)
    if b0 & 0x80 ~= 0 then t[#t + 1] = { a = a, b0 = b0, type = m:read_u8(a + 2), state = m:read_u8(a + 3), x = m:read_u16(a + 8), y = m:read_u16(a + 12), hp = m:read_u8(a + 5), f17 = m:read_u8(a + 17) } end
  end
  return t
end
local held = {}
local function set(name, v) v = v and 1 or 0; if held[name] ~= v then L.F[name]:set_value(v); held[name] = v end end
local function sgn16(v) if v >= 0x8000 then return v - 0x10000 end return v end
local tick, stuckf, lastsig, lastsx = 0, 0, "", -1
local mode = "walk"
local fetching = false
local prevpx, prevpress, blockf, jk = -1, 0, 0, -1  -- blockf: frames a horizontal press moved nothing; jk: jump-kick macro start frame
local tries, wasgrab, grabtarget = {}, false, nil -- grab attempts per pool B record (address:type); a record that gives two empty grabs is skipped
local cleared, started, over = false, false, false
local nstall, ladoff, hop, hopreal = nil, 0, -1, false
local landf, wasbelt = 0, false
local anchor, stagnant = nil, 0
local useban = os.getenv("CB_BAN") == "1" -- CB_BAN=1: skip records that took no damage through 360 frames of fighting (it also skips bosses that are only hurt at times: off by default)
local track, ban = {}, {} -- per pool A record: last hp and the frame it last changed; records that took no damage for 450 frames of fighting are ignored for 1200 frames
local lad, ladtries, baituntil = nil, 0, -1 -- ladder search macro, its attempt count, bait-walk end frame
local clock = 0

local function s16(v) if v >= 0x8000 then return v - 0x10000 end return v end
-- body box of a pool A record: $6b000[type][state] = 4 signed words (R, L, B, T) relative to the record (hit test chain at $f8ca, py/hitbox_gate.py)
local function bodybox(e)
  local a = m:read_u32(0x6b000 + 4 * e.type)
  if a < 0x1000 or a >= 0x80000 then return nil end
  local b = m:read_u32(a + 4 * e.state)
  if b < 0x1000 or b >= 0x80000 then return nil end
  return s16(m:read_u16(b)) + e.x, s16(m:read_u16(b + 2)) + e.x, s16(m:read_u16(b + 4)) + e.y, s16(m:read_u16(b + 6)) + e.y
end
-- would the first jab (box R 40, L 0, B -8, T -32 for a right-facing player, mirrored left) overlap the body box of e from where the player stands?
local function canjab(px, py, face, e)
  local R, Lb, B, T = bodybox(e)
  if not R then return math.abs(e.x - px) < 48 and math.abs(e.y - py) < 24 end
  local ar, al
  if face == 0 then ar, al = px + 40, px else ar, al = px, px - 40 end
  return ar >= Lb and al < R and (py - 8) >= T and (py - 32) < B
end
local function steer(dx, dy, tolx, toly)
  -- returns right, left, up, down toward (dx, dy) until within tolerances
  local r, l, u, d = false, false, false, false
  if math.abs(dy) > toly then if dy < 0 then u = true else d = true end end
  if math.abs(dx) > tolx then if dx > 0 then r = true else l = true end end
  return r, l, u, d
end

local function policy(f)
  local p = 0x80100
  local px, py, face = m:read_u16(p + 8), m:read_u16(p + 12), m:read_u8(p + 7)
  local hold = m:read_u8(p + 58) & 0x80 ~= 0
  local sx, sy = m:read_u16(0x8040a), m:read_u16(0x80406)
  local intro = m:read_u8(p + 3) ~= 0 or m:read_u8(p + 0) & 0x80 == 0 or m:read_u8(p + 90) & 0x40 ~= 0 or m:read_u8(0x80041) & 1 ~= 0
  local r, l, u, d, b1, b2, b3 = false, false, false, false, false, false, false
  if intro then
    for _, n in ipairs { "right", "left", "up", "down", "b1", "b2", "b3" } do set(n, false) end
    return "intro", px, py, face, hold
  end
  tick = tick + 1
  if prevpress ~= 0 and px == prevpx and m:read_u8(p + 4) < 8 then blockf = blockf + 1 elseif px ~= prevpx or prevpress == 0 then blockf = 0 end
  prevpx = px
  -- progress watchdog: neither scroll nor position changed
  local sig = string.format("%04x%04x%04x%08x", px, py, sx, m:read_u32(p + 60)) -- position, scroll and score: any progress
  if sig ~= lastsig then lastsig = sig; stuckf = 0 else stuckf = stuckf + 1 end
  -- stagnation: no scroll, no score and the player has not left a 70 x 60 px window for this many frames (unlike stuckf, hop and seek moves do not reset it)
  local sc = m:read_u32(p + 60)
  if not anchor or math.abs(px - anchor.x) > 70 or math.abs(py - anchor.y) > 60 or sx ~= anchor.sx or sc ~= anchor.sc then anchor = { x = px, y = py, sx = sx, sc = sc }; stagnant = 0 else stagnant = stagnant + 1 end
  local grabbing = m:read_u8(p + 5) == 1 and m:read_u8(p + 27) == 4
  if wasgrab and not grabbing and grabtarget then
    local key = grabtarget.a .. ":" .. grabtarget.type
    if hold then log(f, string.format("GRAB ok type=%d at (%d,%d) player (%d,%d) carry flags %02x", grabtarget.type, grabtarget.x, grabtarget.y, px, py, m:read_u8(p + 26)))
    else tries[key] = (tries[key] or 0) + 1; log(f, string.format("GRAB empty type=%d at (%d,%d) player (%d,%d) try %d", grabtarget.type, grabtarget.x, grabtarget.y, px, py, tries[key])) end
  end
  wasgrab = grabbing
  local E = pool(0x81000, 0x40, 16)
  local B = pool(0x81400, 0x40, 32)
  local en, near = {}, nil
  local nd = 1e9
  for _, e in ipairs(E) do
    local tr = track[e.a]
    if not tr or tr.type ~= e.type or tr.hp ~= e.hp then track[e.a] = { type = e.type, hp = e.hp, n = 0 }; tr = track[e.a] end
    if useban and tr.n > 360 and not (ban[e.a] and ban[e.a] > f) and e.state ~= 0 then ban[e.a] = f + 1200; tr.n = 0; log(f, string.format("ignoring type %d record %x for 1200 frames: hp %d unchanged through 360 frames of fighting it (unreachable or invulnerable)", e.type, e.a, e.hp)) end
    if e.type ~= 0xff and e.state ~= 0 and e.state ~= 2 and e.state ~= 4 and e.state ~= 5 and math.abs(e.x - px) < 300 and math.abs(e.y - py) < 0x50 and not (ban[e.a] and ban[e.a] > f) then
      en[#en + 1] = e
      local d2 = math.abs(e.x - px) + 2 * math.abs(e.y - py)
      if d2 < nd then nd, near = d2, e end
    end
  end
  -- helicopter parts (types 47..49, hit-tested from state 0): they sweep over the arena and come within reach of a standing jab only at the low point of the
  -- sweep (level 2: x 2031..2352, y 288..450; a part's body box reaches 32 px below its y, the jab box 32 above the player's). While one is within 70 px of the
  -- player's y, follow it in x and jab continuously (lab: part hp 32 -> 5 in 150 frames of jabs from x 2179). Level 1's parts hover at y 356 and never qualify.
  local heli = nil
  for _, e in ipairs(E) do if e.type >= 47 and e.type <= 49 and e.hp > 0 and e.y > py - 70 and (not heli or e.y > heli.y) then heli = e end end
  -- level 2 conveyor: the raised block at x >= $900 (y 416 on top of it, y 448 on the ground) moves the player left at 1 px/frame, which cancels a walk, and he drifts off its left edge in
  -- about 25 frames. A right + b2 press about 6 frames after each landing (a fresh b2 edge) jumps on 50 px (lab seqlab.lua S3: x 2329 -> 2380); only at y 400..424 and not airborne (+57 bit 7).
  local belt = want == 2 and not hold and px >= 2290 and sx < 0x9f0 and py >= 400 and py <= 424 and m:read_u8(p + 5) == 0 and m:read_u8(p + 57) & 0x80 == 0 -- y 416 on the block (the ground y in +44 is not a reliable test: the ladder search ran on it)
  if belt then lad = nil end
  if belt and not wasbelt then landf = f end
  wasbelt = belt
  if stuckf > 300 and stuckf <= 700 then near = nil; en = {} end -- no progress for 300 frames: stop chasing, just walk on
  local lockwall, nlw = nil, 1e9
  local lift, nl = nil, 1e9
  for _, b in ipairs(B) do
    do
      if LOCK[b.type] and b.x > px - 8 and b.x - px < nlw then lockwall, nlw = b, b.x - px end
      if LIFT[b.type] and b.b0 & 0x08 == 0 and b.x >= sx + 8 and b.x <= sx + 280 and (tries[b.a .. ":" .. b.type] or 0) < 2 then
        local d2 = math.abs(b.x - px) + 2 * math.abs(b.y - py)
        if HINT[b.type] then d2 = d2 - 100000 end -- props with the PICKUP hint first
        if d2 < nl then lift, nl = b, d2 end
      end
    end
  end
  local mdesc
  if os.getenv("CB_ARENA") and f % 60 == 0 and sx >= tonumber(os.getenv("CB_ARENA"), 16) then -- CB_ARENA=<scroll x in hex, e.g. a00>: every 60 frames the live pool A records while the scroll is at or past it (the last arena of a level)
    local t = {} for _, e in ipairs(E) do t[#t + 1] = string.format("%d:%02x:%d:%d:%d", e.type, e.state, e.x, e.y, e.hp) end
    log(f, string.format("ARENA sx=%x P(%d,%d) mode=%s A %s", sx, px, py, tostring(mode), table.concat(t, " ")))
  end
  if stuckf % 500 == 250 then -- dump what the bot sees when progress stops
    log(f, string.format("STUCK px=%d py=%d sx=%x sy=%x s400=%02x%02x%02x flags40=%02x%02x hold=%s", px, py, sx, sy, m:read_u8(0x80400), m:read_u8(0x80401), m:read_u8(0x80402), m:read_u8(0x80040), m:read_u8(0x80041), tostring(hold)))
    local t = {} for k = 0, 0x7f do t[#t + 1] = string.format("%02x", m:read_u8(p + k)) end
    log(f, "  P " .. table.concat(t))
    if os.getenv("CB_SAVESTALL") and (nstall or 0) < tonumber(os.getenv("CB_SAVESTALL")) then nstall = (nstall or 0) + 1; manager.machine:save(string.format("nb_stall%d", nstall)); L.screen:snapshot(string.format("stall%d.png", nstall)); log(f, "  saved state nb_stall" .. nstall) end
    for _, e in ipairs(E) do log(f, string.format("  A type=%d st=%02x x=%d y=%d hp=%d", e.type, e.state, e.x, e.y, e.hp)) end
    for _, b in ipairs(B) do if b.type ~= 43 and b.type ~= 50 and b.type ~= 53 then log(f, string.format("  B type=%d b0=%02x st=%02x x=%d y=%d", b.type, b.b0, b.state, b.x, b.y)) end end
  end
  -- ladder search: a vertical route (ladder, hole, ledge) accepts the up/down press only on a few px of x (level 4: x 1502..1506): sweep x in 2 px steps pressing the
  -- vertical direction for 6 frames at each. Started when progress stopped for 180 frames and either the scroll is free (no lock) or the only live enemies are on another height.
  local allowed = m:read_u8(0x80401) -- blocked-direction nibble of the scroll cell: bit 0 up, 1 right, 2 down, 3 left
  local lockbit = m:read_u8(0x80400) & 0x20 ~= 0
  local others, od = nil, 1e9
  for _, e in ipairs(E) do
    if e.type ~= 0xff and not (e.type == 28 or (e.type >= 45 and e.type <= 50) or e.type == 65) and e.state ~= 2 and e.state ~= 4 and e.state ~= 5 and math.abs(e.x - px) < 300 and math.abs(e.y - py) >= 0x50 and math.abs(e.y - py) < 0x200 and math.abs(e.x - px) < od then others, od = e, math.abs(e.x - px) end
  end
  if not lad and m:read_u8(p + 5) == 7 and (m:read_u8(p + 4) == 0 or m:read_u8(p + 4) == 4) and not hold then -- already on a ladder (a walk-in): keep climbing the way the scroll cell allows
    lad = { dir = (allowed & 1 == 0) and "up" or "down", offs = { 0 }, i = 1, x0 = px, y0 = py, phase = "climb", t0 = f, moved = f, lasty = py, sx0 = sx }
    log(f, string.format("LADDER already climbing at x=%d y=%d dir=%s", px, py, lad.dir))
  end
  if not lad and not belt and stagnant >= 150 and #en == 0 and not hold and not (lockwall and nlw < 70) and (not lockbit or others) and f >= ladoff then
    local dirs = {}
    if others then dirs[1] = others.y > py and "down" or "up"
    else
      if allowed & 4 == 0 then dirs[#dirs + 1] = "down" end
      if allowed & 1 == 0 then dirs[#dirs + 1] = "up" end
      if #dirs == 0 then dirs = { "down", "up" } end
    end
    local offs = {}
    for k = -20, 20 do offs[#offs + 1] = 2 * k end -- x0-40 .. x0+40, then the wider ring
    for k = 21, 60 do offs[#offs + 1] = -2 * k; offs[#offs + 1] = 2 * k end
    lad = { dir = dirs[(ladtries % #dirs) + 1], offs = offs, i = 1, x0 = px, y0 = py, phase = "go", t0 = f, sx0 = sx }
    ladtries = ladtries + 1
    log(f, string.format("LADDER search start dir=%s from x=%d y=%d (blocked nibble %x, lock %s, other-height enemy %s)", lad.dir, px, py, allowed, tostring(lockbit), others and ("type " .. others.type .. " y " .. others.y) or "none"))
  end
  if lad then
    mdesc = "ladder-" .. lad.phase
    local tx = lad.x0 + lad.offs[lad.i]
    if lad.phase ~= "climb" and ((near and nd < 120) or sx ~= lad.sx0) then log(f, "LADDER search aborted (enemy near or scroll moved)"); lad = nil; stuckf = 0; ladoff = f + 600 end
    if lad and lad.phase == "go" then
      if px < tx then r = true elseif px > tx then l = true end
      if px == tx then lad.phase = "press"; lad.t0 = f; lad.y0 = py
      elseif f - lad.t0 > 60 then lad.i = lad.i + 1; lad.t0 = f end
    elseif lad and lad.phase == "press" then
      local k = f - lad.t0
      if k < 6 then if lad.dir == "down" then d = true else u = true end end
      if m:read_u8(p + 5) == 7 or math.abs(py - lad.y0) > 8 then lad.phase = "climb"; lad.t0 = f; lad.moved = f; lad.lasty = py; log(f, string.format("LADDER found at x=%d (%s), sub-action %d", px, lad.dir, m:read_u8(p + 5)))
      elseif k >= 8 then lad.i = lad.i + 1; lad.phase = "go"; lad.t0 = f end
    elseif lad and lad.phase == "climb" then
      if lad.dir == "down" then d = true else u = true end
      if py ~= lad.lasty then lad.lasty = py; lad.moved = f end
      if f - lad.moved > 45 or f - lad.t0 > 900 then log(f, string.format("LADDER climb ends at x=%d y=%d", px, py)); lad = nil; stuckf = 0 end
    end
    if lad and lad.i > #lad.offs then log(f, "LADDER sweep failed"); lad = nil; stuckf = 300; ladoff = f + 1500 end
    if lad then
      set("right", r); set("left", l); set("up", u); set("down", d); set("b1", false); set("b2", false); set("b3", false)
      prevpress = (r or l) and 1 or 0
      return mdesc, px, py, face, hold, #en
    end
  end
  if stuckf > 700 then -- watchdog: wiggle and mash for a while
    local k = (f // 9) % 8
    r = k == 0 or k == 1 or k == 6; l = k == 3; u = k == 2; d = k == 4
    b1 = f % 6 < 2; b3 = k == 5 and f % 4 < 2
    mdesc = "watchdog"
    if stuckf > 800 then stuckf = 0 end
  elseif belt then
    mdesc = "belt-hop"; stuckf = 0; r = true
    b2 = f - landf >= 6 and f - landf < 30
  elseif heli and not hold then
    mdesc = "heli"; stuckf = 0
    local dx = heli.x - px
    if math.abs(dx) > 10 then r, l = dx > 0, dx < 0 end
    if tick % 6 < 2 then b1 = true end
  elseif hold then
    fetching = false
    local flags = m:read_u8(p + 26)
    local tgt = near and math.abs(near.x - px) < 140 and math.abs(near.y - py) < 40 and near or lockwall
    if tgt then
      local dx, dy = tgt.x - px, tgt.y - py
      mdesc = "carry>throw"
      local tol = 90
      r, l, u, d = steer(dx, dy, tol, 6)
      if math.abs(dx) <= tol and math.abs(dy) <= 10 then
        -- face it, then throw
        if (dx > 0) ~= (face == 0) then r, l = dx > 0, dx < 0; mdesc = "carry>turn"
        elseif tick % 6 < 3 then b3 = true end
        r, l = false, false
        if (dx > 0) ~= (face == 0) then r, l = dx > 0, dx < 0 end
      end
    else
      r = true; mdesc = "carry>walk"
      if stuckf > 60 and tick % 8 < 3 then b3 = true end
    end
  elseif near and (nd < 150 or #en > 0 and not lockwall) then
    mdesc = "fight"
    if track[near.a] then track[near.a].n = track[near.a].n + 1 end
    local dx, dy = near.x - px, near.y - py
    local want = (dx > 0) == (face == 0) -- facing it
    if jk >= 0 then -- jump kick macro: jump toward the enemy, kick at the top of the jump (b1 during the jump, +6 = 1)
      local k = f - jk
      mdesc = "jumpkick"
      r, l = dx > 0, dx < 0
      b2 = k < 3
      b1 = k >= 14 and k < 17
      if k > 40 then jk = -1 end
    elseif f < baituntil then
      mdesc = "bait"; r, l = dx < 0, dx > 0 -- back away so that it walks on screen
    elseif want and canjab(px, py, face, near) then
      mdesc = "jab"
      if tick % 5 == 0 or tick % 5 == 1 then b1 = true end -- the jab chain is extended by a second press in frames 2-11 of the first
    else
      -- not in reach: close the distance, turning if needed (a press toward it also faces it)
      r, l = dx > 0, dx < 0
      if math.abs(dx) < 40 then r, l = false, false; if not want then r, l = dx > 0, dx < 0 end end
      if math.abs(dx) < 56 and math.abs(dy) > 8 then -- right column but wrong row: a lane change if the terrain has one, else the jump kick
        if dy > 8 then d = true else u = true end
      end
      if blockf > 60 or (math.abs(dx) < 70 and not canjab(px, py, face, near) and tick % 240 > 150) then
        if (f // 97) % 2 == 0 and blockf > 60 then baituntil = f + 90 else jk = f end
      end
    end
  elseif lockwall and nlw < 70 and stuckf < 500 and not fetching then
    mdesc = "wall-punch" -- a lock wall is solid but breaks under repeated b1 hits (lab3: 3 hits, about 100 frames)
    r = true
    if tick % 6 < 2 then b1 = true end
  elseif lockwall and lift and (fetching and nlw < 300 or stuckf >= 500 and nlw < 120) then
    fetching = true
    mdesc = "fetch"
    grabtarget = lift
    if stuckf > 90 then local key = lift.a .. ":" .. lift.type; tries[key] = (tries[key] or 0) + 1; stuckf = 0; log(f, string.format("fetch blocked: skip type=%d at (%d,%d) player (%d,%d)", lift.type, lift.x, lift.y, px, py)) end
    local side = lift.x >= px and 1 or -1
    local dx, dy = lift.x - side * 24 - px, lift.y - py -- stand 24 px short of the prop (the carrylab geometry), same y
    r, l, u, d = steer(dx, dy, 4, 1)
    if math.abs(dx) <= 6 and math.abs(dy) <= 2 then
      if (side > 0) ~= (face == 0) then r, l = side > 0, side < 0 else r, l = false, false end
      if (side > 0) == (face == 0) and tick % 24 < 3 then b3 = true end
    end
  elseif lockwall and nlw < 120 then
    fetching = false
    mdesc = "wall-walk"
    r = nlw > 24
  else
    mdesc = "walk"
    r = true
    if near then if tick % 5 == 0 then b1 = true end end
    if others and stuckf > 120 and hop < 0 and not lockwall then -- the live enemies are on another height: walk toward them, down (or up) pressed, off the ledge or onto the ladder
      mdesc = "seek-lane"
      r, l = others.x > px + 8, others.x < px - 8
      if others.y > py then d = true else u = true end
    elseif hop >= 0 then
      local k = f - hop
      mdesc = "hop"; r = true
      if hopreal then -- terrain in the way (nothing to punch ahead): the walk-punch phase just before keeps the player in the punch chain for about 40 frames, and a b2 that goes down during it
        b2 = k >= 42 and k < 72 -- is lost (it is an edge, holding on does not start the jump): wait, then press (lab seqlab.lua, level 2 x 2291: G jumps, E and F do not)
        if k > 80 then hop = -1; blockf = 0 end
      else
        b2 = k < 3 -- an object ahead: the original hop, which a punch in progress swallows (level 1 relies on the pause between punch phases; a real jump there loses the clear)
        if k > 44 then hop = -1; blockf = 0 end
      end
    elseif blockf > 20 then -- blocked: something solid (a drum, a wall) is in the way: break it; or a step too high to walk onto: jump it (jump height 48, 1.75 px/frame forward for 32 frames)
      if (blockf // 40) % 2 == 1 and not lockbit then -- not inside a lock zone: there the blocker is the screen edge and the fight comes to you
        hop = f; hopreal = true
        for _, e in ipairs(E) do if e.x > px and e.x - px < 70 and math.abs(e.y - py) < 48 then hopreal = false end end
        for _, b in ipairs(B) do if b.type ~= 43 and b.type ~= 50 and b.type ~= 53 and b.x > px and b.x - px < 70 and math.abs(b.y - py) < 48 then hopreal = false end end
      else mdesc = "walk-punch"; if tick % 6 < 2 then b1 = true end end
    end
  end
  set("right", r); set("left", l); set("up", u); set("down", d); set("b1", b1); set("b2", b2); set("b3", b3)
  prevpress = (r or l) and 1 or 0
  return mdesc, px, py, face, hold, #en
end

-- CB_CAPTURE=N: up to N captures (RAM $80000-$83fff as capNNNNN.ram next to a screenshot capNNNNN.png in $CB_RUN/snap) at frames where the player's attack
-- flag (+28) is set with a live pool A record within 56 px, at least CB_CAPGAP (default 45) frames apart: input of py/overlay.py
local capmax = tonumber(os.getenv("CB_CAPTURE") or "0")
local capgap = tonumber(os.getenv("CB_CAPGAP") or "45")
local ncap, lastcap = 0, -9999
local function capture(f)
  if ncap >= capmax or f - lastcap < capgap or m:read_u8(0x80100 + 28) == 0 then return end
  local px, py = m:read_u16(0x80108), m:read_u16(0x8010c)
  for i = 0, 15 do
    local a = 0x81000 + i * 0x40
    if m:read_u8(a) & 0x80 ~= 0 and math.abs(m:read_u16(a + 8) - px) < 56 and math.abs(m:read_u16(a + 12) - py) < 24 then
      ncap, lastcap = ncap + 1, f
      L.screen:snapshot(string.format("cap%05d.png", f))
      L.write(string.format("%s/cap%05d.ram", out, f), L.ram())
      log(f, string.format("capture %d (enemy type %d state %02x)", ncap, m:read_u8(a + 2), m:read_u8(a + 3)))
      return
    end
  end
end
-- CB_ENEMYLOG=1: write enemylog.txt in the format of enemies1/lua/enemylog.lua (F, P, R and H lines every frame), the input of enemies1/py/census.py and loglib.py
local elog = os.getenv("CB_ENEMYLOG") == "1" and io.open(out .. "/enemylog.txt", "w") or nil
local function hexs(base, n) local t = {} for k = 0, n - 1 do t[#t + 1] = string.format("%02x", m:read_u8(base + k)) end return table.concat(t) end
local function enemylog(f)
  elog:write(string.format("F %d %04x %04x %02x%02x lvl=%d s400=%02x%02x%02x%02x e=%02x%02x\n", f, m:read_u16(0x8040a), m:read_u16(0x80406), m:read_u8(0x80040), m:read_u8(0x80041), m:read_u8(0x80046), m:read_u8(0x80400), m:read_u8(0x80401), m:read_u8(0x80402), m:read_u8(0x80403), m:read_u8(0x81e02), m:read_u8(0x81e03)))
  elog:write(string.format("P %d %s\n", f, hexs(0x80100, 0x80)))
  for i = 0, 15 do local b = 0x81000 + i * 0x40; if m:read_u8(b) & 0x80 ~= 0 then elog:write(string.format("R %d %d %s\n", f, i, hexs(b, 64))) end end
  for i = 0, 7 do local b = 0x81c00 + i * 0x20; if m:read_u8(b) & 0x80 ~= 0 then elog:write(string.format("H %d %d %s\n", f, i, hexs(b, 32))) end end
end
local loaded = false
emu.register_frame_done(function()
  local f = L.frame()
  if os.getenv("CB_LOAD") and not loaded then loaded = true; manager.machine:load(os.getenv("CB_LOAD")); return end
  if not os.getenv("CB_LOAD") then
    if f == 600 then L.F.coin:set_value(1) elseif f == 612 then L.F.coin:set_value(0)
    elseif f == 700 then L.F.start1:set_value(1) elseif f == 712 then L.F.start1:set_value(0) end
  end
  local running = m:read_u8(0x80040) & 0x80 ~= 0
  local mdesc, px, py, face, hold, ne = "idle", 0, 0, 0, false, 0
  if running and f >= (os.getenv("CB_LOAD") and 0 or 900) then
    if god then m:write_u8(0x80113, 0x38); m:write_u16(0x80136, 0x7fff) end
    if keeptimer and m:read_u16(0x80042) < 0x0100 then m:write_u16(0x80042, 0x0300); log(f, "timer refilled") end
    mdesc, px, py, face, hold, ne = policy(f)
    capture(f)
    if elog then enemylog(f) end
    if mdesc ~= mode then log(f, "mode " .. mdesc); mode = mdesc end
    if f % logn == 0 then
      local p = 0x80100
      csv:write(string.format("%d,%d,%d,%d,%d,%d,%d,%d,%d,%08x,%x,%x,%d,%d,%02x,%02x,%s\n", f, px, py, face, m:read_u8(p + 4), m:read_u8(p + 5), hold and 1 or 0,
        m:read_u8(p + 19), m:read_u8(p + 20), m:read_u32(p + 60), m:read_u16(0x8040a), m:read_u16(0x80406), ne or 0, m:read_u8(0x80046), m:read_u8(0x80040), m:read_u8(0x80400), mdesc))
    end
  end
  if f >= slo and f <= shi and (f - slo) % sst == 0 then L.screen:snapshot(string.format("n%05d.png", f)) end
  if saveat[f] then manager.machine:save(saveat[f]); log(f, "saved " .. saveat[f]) end
  if m:read_u8(0x80040) & 0x10 ~= 0 and not cleared then
    cleared = true; log(f, "LEVEL CLEARED flag $80040 bit 4"); manager.machine:save("nb_clear")
    for _, n in ipairs { "right", "left", "up", "down", "b1", "b2", "b3" } do set(n, false) end
    if f + 600 < stop then stop = f + 600 end
  end
  if running and m:read_u8(0x80100) & 3 ~= 0 and not over then over = true; log(f, "PLAYER 1 OUT (record mode " .. (m:read_u8(0x80100) & 3) .. "): timer or health reached 0"); stop = math.min(stop, f + 60) end
  if f >= stop then csv:close(); ev:close(); if elog then elog:close() end manager.machine:exit() end
end)
