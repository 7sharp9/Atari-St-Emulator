-- drive5.lua: level start + scripted pokes + per-frame object log, for the L5A group (derived from enemies2/lua/objlog.lua).
-- env:  CB_DIR (reversing/crudebuster/lua)  CB_LEVEL (0-5)  CB_STOP (last frame)  CB_OUT (dir, writes objlog.txt)
--   CB_BOT   0 none | 1 walk right + attack nearest pool A record (objlog's bot) | 2 "chase": every frame put P1 beside the nearest
--            pool A record (side alternates every 90 frames) and press button 1 in 4-on/4-off phases (no walking needed)
--   CB_BLOCK 1 = set $81e03 bit 7 every frame (no script spawns, so a CB_SPAWN type is met alone)
--   CB_FOLLOW 1 (bot 2) also set the x scroll counter to enemy x - $80 each frame; CB_FOLLOWY 1 the y counter to enemy y - $c0
--   CB_INJECT 1 = synthetic player hit: +6 |= $80 on a record whose state has lasted exactly 5 frames (states 0,1,2 and type $41 excluded); I lines
--   CB_INJAT n (frames in the state before the injection, default 5), CB_INJSTATES "b,c,d" (hex csv: inject only in these states; records with +0 bit 3 set are skipped)
--   CB_INJREFILL 1 = set health to 12 when an injected record is down to 3 or less (keeps the record alive for a long census)
--   CB_INJOFS / CB_INJVAL (hex byte offset and OR-value, default 6 / 80; 17 / 40 = the throw/ground hit flag of $22dac; 6 / 88 = a strong hit)
--   CB_NOATK 1 = the bot never presses button 1
--            5 "wander": P1 never attacks and stands at a cycling x distance (20..330 px, 60 frames each), y offset (0, -$70, +$30; 360 frames each) and side (540 frames) from the nearest pool A record
--   CB_HP    1 = restore P1 health to its start value at the end of each frame (the F line shows the value BEFORE the restore, so a drop = damage)
--   CB_HP2   1 = same for P2 ($80180 +19)
--   CB_SPAWN "frame:type:variant:x:y;..."  (hex) write a pool A record into the first free slot at that frame (what $f388 does:
--            +0 = $80, +2 type, +16 variant, +8 x word, +12 y word). Lets a type be met in isolation.
--   CB_PTR   "frame:addr"  (hex) set the list A pointer $81e06 (long) = next script entry to be spawned
--   CB_PTRB  "frame:addr"  (hex) set the list B pointer $81e0a (long); level 5 list B ($6d572, 6 entries, terminator at $6d5a2)
--   CB_SCROLL "frame:x:y"  (hex) set the scroll counter words $8040a (x) and $80406 (y)
--   CB_HOLDSCROLL "x:y" (hex) set the scroll counters $8040a/$80406 every frame from frame 799 (an arena that must not scroll)
--   CB_HOLDSCROLL2 "frame:x:y" (hex x,y) from that frame the held scroll value is this one instead
--   CB_P1    "frame:x:y;..." (hex) set P1 x ($80108) and y ($8010c) words once at that frame ; CB_P1HOLD "x:y" every frame from frame 721
--   CB_POKES "frame:addr:byte,..." (hex)   CB_POKEW "frame:addr:word,..." (hex word)
--   CB_POOLB / CB_POOLC  1 = log pool B / pool C records (C lines are 32 bytes)
--   CB_SAVE / CB_SAVE_FRAME, CB_SHOTS "lo:hi:step" (screenshots o%05d.png into the run dir's snap/)
--   CB_KEEPSCROLLX / none: the stock scroll logic is untouched unless CB_SCROLL is used.
-- lines:  F frame lvl sx sy px py hp f40 f41 n  f400 p1state p1sub p1b1(held) p1score
--         A frame slot <64 hex bytes>   B/C likewise
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "5")
local stop = tonumber(os.getenv("CB_STOP") or "2000")
local bot = tonumber(os.getenv("CB_BOT") or "0")
local keephp = tonumber(os.getenv("CB_HP") or "1")
local keephp2 = tonumber(os.getenv("CB_HP2") or "0")
local logb = tonumber(os.getenv("CB_POOLB") or "0")
local logc = tonumber(os.getenv("CB_POOLC") or "0")
local out = io.open((os.getenv("CB_OUT") or ".") .. "/objlog.txt", "w")
local slo, shi, sst = 0, -1, 1
if os.getenv("CB_SHOTS") then slo, shi, sst = os.getenv("CB_SHOTS"):match("(%d+):(%d+):(%d+)"); slo, shi, sst = tonumber(slo), tonumber(shi), tonumber(sst) end
local m = L.mem
local cpu = manager.machine.devices[":maincpu"]
local function split(s, sep) local t = {}; for w in (s or ""):gmatch("[^" .. sep .. "]+") do t[#t + 1] = w end; return t end
local ev = {} -- frame -> list of functions
local function at(f, fn) ev[f] = ev[f] or {}; table.insert(ev[f], fn) end
for _, s in ipairs(split(os.getenv("CB_POKES"), ",")) do
  local f, a, b = s:match("(%d+):(%x+):(%x+)"); f, a, b = tonumber(f), tonumber(a, 16), tonumber(b, 16)
  at(f, function() m:write_u8(a, b) end)
end
for _, s in ipairs(split(os.getenv("CB_POKEW"), ",")) do
  local f, a, b = s:match("(%d+):(%x+):(%x+)"); f, a, b = tonumber(f), tonumber(a, 16), tonumber(b, 16)
  at(f, function() m:write_u16(a, b) end)
end
for _, s in ipairs(split(os.getenv("CB_SPAWN"), ";")) do
  local f, t, v, x, y = s:match("(%d+):(%x+):(%x+):(%x+):(%x+)")
  f, t, v, x, y = tonumber(f), tonumber(t, 16), tonumber(v, 16), tonumber(x, 16), tonumber(y, 16)
  at(f, function()
    for i = 0, 15 do
      local base = 0x81000 + 0x40 * i
      if (m:read_u8(base) & 0x80) == 0 then
        for k = 0, 0x3f do m:write_u8(base + k, 0) end
        m:write_u8(base, 0x80); m:write_u8(base + 2, t); m:write_u8(base + 16, v); m:write_u16(base + 8, x); m:write_u16(base + 12, y)
        return
      end
    end
  end)
end
for _, s in ipairs(split(os.getenv("CB_PTR"), ";")) do
  local f, a = s:match("(%d+):(%x+)"); f, a = tonumber(f), tonumber(a, 16)
  at(f, function() m:write_u32(0x81e06, a) end)
end
for _, s in ipairs(split(os.getenv("CB_PTRB"), ";")) do
  local f, a = s:match("(%d+):(%x+)"); f, a = tonumber(f), tonumber(a, 16)
  at(f, function() m:write_u32(0x81e0a, a) end)
end
for _, s in ipairs(split(os.getenv("CB_SCROLL"), ";")) do
  local f, x, y = s:match("(%d+):(%x+):(%x+)"); f, x, y = tonumber(f), tonumber(x, 16), tonumber(y, 16)
  at(f, function() m:write_u16(0x8040a, x); m:write_u16(0x80406, y) end)
end
for _, s in ipairs(split(os.getenv("CB_P1"), ";")) do
  local f, x, y = s:match("(%d+):(%x+):(%x+)"); f, x, y = tonumber(f), tonumber(x, 16), tonumber(y, 16)
  at(f, function() m:write_u16(0x80108, x); m:write_u16(0x8010c, y) end)
end
local sh = nil
if os.getenv("CB_HOLDSCROLL") then local x, y = os.getenv("CB_HOLDSCROLL"):match("(%x+):(%x+)"); sh = { tonumber(x, 16), tonumber(y, 16) } end
local sh2 = nil
if os.getenv("CB_HOLDSCROLL2") then local f, x, y = os.getenv("CB_HOLDSCROLL2"):match("(%d+):(%x+):(%x+)"); sh2 = { tonumber(f), tonumber(x, 16), tonumber(y, 16) } end
local hold = nil
if os.getenv("CB_P1HOLD") then local x, y = os.getenv("CB_P1HOLD"):match("(%x+):(%x+)"); hold = { tonumber(x, 16), tonumber(y, 16) } end
taps = {}
taps[1] = m:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return (data & 0xff) ~= data and data or ((want << 8) | want) end
end)

-- event taps (lines H, S, Z): H = a write to a player's health (+19) from the hit code ($fc9e): A6 = pool C hit box, owner = its +28
inlua = false
local function areg(n) return cpu.state[n].value end
local function owner_info(c)
  local o = m:read_u32(c + 28)
  if o >= 0x81000 and o < 0x81400 then return string.format("%02x %02x %d", m:read_u8(o + 2), m:read_u8(o + 3), (o - 0x81000) // 0x40) end
  return "-- -- -"
end
taps[2] = m:install_write_tap(0x80112, 0x80113, "hp1", function(off, data, mask)
  if (mask & 0xff) == 0 or inlua then return end
  local pc = cpu.state["CURPC"].value
  out:write(string.format("H %d P1 pc=%06x old=%02x new=%02x ctype=%02x owner %s\n", L.frame(), pc, m:read_u8(0x80113), data & 0xff, m:read_u8(areg("A6") + 2), owner_info(areg("A6"))))
end)
taps[3] = m:install_write_tap(0x80192, 0x80193, "hp2", function(off, data, mask)
  if (mask & 0xff) == 0 or inlua then return end
  local pc = cpu.state["CURPC"].value
  out:write(string.format("H %d P2 pc=%06x old=%02x new=%02x ctype=%02x owner %s\n", L.frame(), pc, m:read_u8(0x80193), data & 0xff, m:read_u8(areg("A6") + 2), owner_info(areg("A6"))))
end)
taps[4] = m:install_write_tap(0x81c00, 0x81dff, "cspawn", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x21e88 and pc <= 0x21e98 and ((off - 0x81c00) % 0x20) == 2 then
    local a6 = areg("A6")
    out:write(string.format("S %d ctype=%02x owner_type=%02x owner_state=%02x owner_slot=%d face=%d anim=%d\n", L.frame(), (data >> 8) & 0xff, m:read_u8(a6 + 2), m:read_u8(a6 + 3), (a6 - 0x81000) // 0x40, m:read_u8(a6 + 4), m:read_u8(a6 + 20)))
  end
end)
taps[5] = m:install_write_tap(0xbc002, 0xbc003, "snd", function(off, data, mask)
  out:write(string.format("Z %d snd=%02x pc=%06x\n", L.frame(), data & 0xff, cpu.state["CURPC"].value))
end)
local runst = {}
local injofs = tonumber(os.getenv("CB_INJOFS") or "6", 16)
local injval = tonumber(os.getenv("CB_INJVAL") or "80", 16)
local injat = tonumber(os.getenv("CB_INJAT") or "5")
local injst = nil
if os.getenv("CB_INJSTATES") then injst = {}; for h in os.getenv("CB_INJSTATES"):gmatch("%x+") do injst[tonumber(h, 16)] = true end end
local hp0, hp20 = nil, nil
local atk_phase = 0
local function set(name, v) L.F[name]:set_value(v) end
local function bytes(base, n)
  local t = {}
  for k = 0, n - 1 do t[#t + 1] = string.format("%02x", m:read_u8(base + k)) end
  return table.concat(t)
end
emu.register_frame_done(function()
  local f = L.frame()
  if f == 800 then out:write(string.format("D %d dip54=%04x dip55=%02x\n", f, m:read_u16(0x80054), m:read_u8(0x80055))) end
  if f == 600 then set("coin", 1) elseif f == 612 then set("coin", 0)
  elseif f == 700 then set("start1", 1) elseif f == 712 then set("start1", 0) end
  if ev[f] then for _, fn in ipairs(ev[f]) do fn() end end
  local running = (m:read_u8(0x80040) & 0x80) ~= 0 and f > 720
  if sh2 and f >= sh2[1] then m:write_u16(0x8040a, sh2[2]); m:write_u16(0x80406, sh2[3]) elseif sh and f >= 799 then m:write_u16(0x8040a, sh[1]); m:write_u16(0x80406, sh[2]) end
  if hold and running then m:write_u16(0x80108, hold[1]); m:write_u16(0x8010c, hold[2]) end
  local px, py = m:read_u16(0x80108), m:read_u16(0x8010c)
  local hp = m:read_u8(0x80113)
  if running and hp0 == nil and hp > 0 then hp0 = hp end
  inlua = true
  if running and keephp == 1 and hp0 then m:write_u8(0x80113, hp0) end
  local hp2 = m:read_u8(0x80193)
  if running and hp20 == nil and hp2 > 0 then hp20 = hp2 end
  if running and keephp2 == 1 and hp20 then m:write_u8(0x80193, hp20) end
  inlua = false
  if os.getenv("CB_BLOCK") == "1" and running then m:write_u8(0x81e03, 0x80) end
  if os.getenv("CB_INJECT") == "1" and running then
    -- synthetic player hit: when a record has been in the same state for exactly 5 frames, set +6 bit 7 (what the player attack test $f82e writes); logged as I lines
    for i = 0, 15 do
      local base = 0x81000 + 0x40 * i
      if (m:read_u8(base) & 0x80) ~= 0 then
        local st = m:read_u8(base + 3)
        local ty = m:read_u8(base + 2)
        local r = runst[i]
        if r and r[1] == st and r[3] == ty then r[2] = r[2] + 1 else runst[i] = { st, 1, ty }; r = runst[i] end
        if r[2] == injat and (injst == nil or injst[st]) and (m:read_u8(base) & 8) == 0 and st ~= 0 and st ~= 1 and st ~= 2 and ty ~= 0x41 then
          m:write_u8(base + injofs, m:read_u8(base + injofs) | injval)
          if m:read_u8(base + 5) <= 3 and os.getenv("CB_INJREFILL") == "1" then m:write_u8(base + 5, 12) end
          out:write(string.format("I %d slot=%d type=%02x state=%02x hp=%d\n", f, i, ty, st, m:read_u8(base + 5)))
        end
      else runst[i] = nil end
    end
  end
  local n = 0
  for i = 0, 15 do
    local base = 0x81000 + 0x40 * i
    if (m:read_u8(base) & 0x80) ~= 0 then n = n + 1; out:write(string.format("A %d %d %s\n", f, i, bytes(base, 64))) end
  end
  if logb == 1 then
    for i = 0, 31 do
      local base = 0x81400 + 0x40 * i
      if (m:read_u8(base) & 0x80) ~= 0 then out:write(string.format("B %d %d %s\n", f, i, bytes(base, 64))) end
    end
  end
  if logc == 1 then
    for i = 0, 7 do
      local base = 0x81c00 + 0x20 * i
      if (m:read_u8(base) & 0x80) ~= 0 then out:write(string.format("C %d %d %s\n", f, i, bytes(base, 32))) end
    end
  end
  out:write(string.format("F %d %d %04x %04x %04x %04x %02x %02x %02x %d %02x %02x %02x %02x %08x %08x %02x %02x\n", f, m:read_u8(0x80046), m:read_u16(0x8040a), m:read_u16(0x80406), px, py, hp,
    m:read_u8(0x80040), m:read_u8(0x80041), n, m:read_u8(0x80400), m:read_u8(0x80118), m:read_u8(0x80119), m:read_u8(0x80051) & 0x10, m:read_u32(0x8013c), m:read_u32(0x81e06), m:read_u8(0x81e03), m:read_u8(0x81e04)))
  if bot >= 1 and running then
    local best, bd, bi = nil, 1e9, nil
    for i = 0, 15 do
      local base = 0x81000 + 0x40 * i
      if (m:read_u8(base) & 0x80) ~= 0 then
        local ex, ey = m:read_u16(base + 8), m:read_u16(base + 12)
        local d = math.abs(ex - px) + 3 * math.abs(ey - py)
        if d < bd then best, bd, bi = { ex, ey }, d, i end
      end
    end
    local l, r, u, d = 0, 0, 0, 0
    local hit = 0
    if bot == 5 and best then
      -- wander: P1 stands at a cycling x distance (every 60 frames) and y offset (every 360 frames) from the nearest record, never attacks
      local dxs = { 20, 40, 70, 100, 140, 180, 230, 280, 330 }
      local dys = { 0, -0x70, 0x30, 0 }
      local dk = dxs[((f // 60) % #dxs) + 1]
      local yk = dys[((f // 360) % #dys) + 1]
      local side = ((f // 540) % 2 == 0) and -1 or 1
      local tx, ty = best[1] + side * dk, best[2] + yk
      if tx < 0x20 then tx = best[1] + dk end
      m:write_u16(0x80108, tx); m:write_u16(0x8010c, ty)
      if os.getenv("CB_FOLLOW") == "1" then m:write_u16(0x8040a, math.max(0x100, best[1] - 0x80)) end
      if os.getenv("CB_FOLLOWY") == "1" then m:write_u16(0x80406, math.max(0x100, best[2] - 0xc0)) end
      if side < 0 then r = 1 else l = 1 end
    end
    if bot == 2 and best then
      local side = ((f // 90) % 2 == 0) and -1 or 1
      local tx, ty = best[1] + side * 40, best[2]
      if tx < 0x20 then tx = best[1] + 40; side = 1 end
      m:write_u16(0x80108, tx); m:write_u16(0x8010c, ty)
      if os.getenv("CB_FOLLOW") == "1" then m:write_u16(0x8040a, math.max(0x100, best[1] - 0x80)) end
      if os.getenv("CB_FOLLOWY") == "1" then m:write_u16(0x80406, math.max(0x100, best[2] - 0xc0)) end
      if side < 0 then r = 1 else l = 1 end
      atk_phase = (atk_phase + 1) % 8
      hit = atk_phase < 4 and 1 or 0
    elseif bot == 1 and best and bd < 400 then
      local dx, dy = best[1] - px, best[2] - py
      if dy < -4 then u = 1 elseif dy > 4 then d = 1 end
      if dx > 36 then r = 1 elseif dx < -36 then l = 1 end
      if math.abs(dx) < 56 and math.abs(dy) < 14 then
        if dx > 0 then r = 1 else l = 1 end
        atk_phase = (atk_phase + 1) % 8
        hit = atk_phase < 4 and 1 or 0
      end
    elseif bot == 1 then
      r = 1
    end
    if os.getenv("CB_NOATK") == "1" then hit = 0 end
    set("right", r); set("left", l); set("up", u); set("down", d); set("b1", hit)
  end
  if f >= slo and f <= shi and (f - slo) % sst == 0 then L.screen:snapshot(string.format("o%05d.png", f)) end
  if os.getenv("CB_SAVE") and f == tonumber(os.getenv("CB_SAVE_FRAME")) then manager.machine:save(os.getenv("CB_SAVE")) end
  if f >= stop then out:close(); manager.machine:exit() end
end)
