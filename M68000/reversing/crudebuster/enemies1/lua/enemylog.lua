-- enemylog.lua: start a level, play it with a simple bot (walk right, close on the nearest pool A enemy, mash attack), keep P1 alive,
-- and log every active pool A record (64 bytes) each frame.
-- env: CB_SAVES (name:frame,... several states), CB_LOAD (state name in $CB_RUN/sta/cbuster/: loaded at the 3rd frame; the frame counter continues from the saved one), CB_DIR (reversing/crudebuster/lua), CB_LEVEL (0-5), CB_STOP (frame), CB_OUT (dir), CB_BOT (1 = bot, 0 = walk right only, 2 = stand still),
--      CB_GOD (1: poke P1 health $80113 = $38 (full health: the bar routine $3d66 draws 7 segments for $38 and corrupts the tilemap RAM for a value of $40 or more) every frame), CB_FROM (first frame to log), CB_SAVE/CB_SAVE_FRAME, CB_LOAD not used.
-- output: enemylog.txt  lines:  F frame sx sy | P1 hex(first 0x80 bytes of $80100)
--                               R frame slot hex(64 bytes)         (one per active pool A record)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local stop = tonumber(os.getenv("CB_STOP") or "3000")
local bot = tonumber(os.getenv("CB_BOT") or "1")
local god = tonumber(os.getenv("CB_GOD") or "1")
local from = tonumber(os.getenv("CB_FROM") or "0")
local slo, shi, sst = 0, -1, 1
if os.getenv("CB_SHOTS") then slo, shi, sst = os.getenv("CB_SHOTS"):match("(%d+):(%d+):(%d+)"); slo, shi, sst = tonumber(slo), tonumber(shi), tonumber(sst) end
local out = io.open((os.getenv("CB_OUT") or ".") .. "/enemylog.txt", "w")
local cpu = manager.machine.devices[":maincpu"]
local m = L.mem
taps = {}
taps[1] = m:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return (data & 0xff) ~= data and data or ((want << 8) | want) end
end)
local function hex(base, n) local t = {} for k = 0, n - 1 do t[#t + 1] = string.format("%02x", m:read_u8(base + k)) end return table.concat(t) end
local held = {}
local cleared
local assist = tonumber(os.getenv("CB_ASSIST") or "0")  -- a pool A enemy still alive this many frames after its spawn gets a light-hit flag poked into +6 every 25 frames (the game's own hit/death path runs), so the level keeps going
local portrait = tonumber(os.getenv("CB_PORTRAIT") or "0")  -- snapshot each new (type, variant) up to N times while on screen: p<frame>_t<type>_v<var>_s<state>.png + an S line
local shots, lastshot = {}, {}
local born = {}
local assisted = {}
local function set(name, v) if held[name] ~= v then L.F[name]:set_value(v); held[name] = v end end
local lastchg, lastsig = 0, ""
local function dobot(f)
  if f < 740 then return end
  local sig = string.format("%04x%04x%02x", m:read_u16(0x80108), m:read_u16(0x8010c), m:read_u8(0x80118))
  if sig ~= lastsig then lastsig = sig; lastchg = f end
  if f - lastchg > 240 and m:read_u8(0x80118) == 7 and m:read_u8(0x81e02) == 0 then -- P is stuck in the 'held' action (7) although no pool A enemy lives: the holder was removed by the assist, free the player
    m:write_u8(0x80158, m:read_u8(0x80158) & 0x6f); m:write_u8(0x80118, 0); lastchg = f
    out:write(string.format("U %d freed P1 from action 7 (artifact of the assist)\n", f))
  end
  if f - lastchg > 240 then -- watchdog: the player has not moved or changed action for 240 frames: wiggle and mash for 60 frames
    if f - lastchg > 300 then lastchg = f end
    local k = (f // 7) % 6
    set("right", (k == 0 or k == 1) and 1 or 0); set("left", k == 3 and 1 or 0); set("up", k == 2 and 1 or 0); set("down", k == 4 and 1 or 0)
    set("b1", (f % 4 < 2) and 1 or 0); return
  end
  local px, py = m:read_u16(0x80108), m:read_u16(0x8010c)
  local best, bd
  for i = 0, 15 do
    local b = 0x81000 + 0x40 * i
    if m:read_u8(b) & 0x80 ~= 0 then
      local ddx, ddy = math.abs(m:read_u16(b + 8) - px), math.abs(m:read_u16(b + 12) - py)
      local d = ddx + 2 * ddy
      if ddy < 0x40 and ddx < 0xa0 and (not bd or d < bd) then bd = d; best = b end -- only enemies on the player's lane within 160 px count as targets
    end
  end
  if bot == 2 then return end
  if bot == 4 then -- walk right until an enemy is within 120 px, then stand still (no attack): enemies get to attack a passive player
    local near = best and math.abs(m:read_u16(best + 8) - px) < 120
    set("right", near and 0 or 1); set("b1", 0); return
  end
  if bot == 3 then set("right", 1); return end
  if bot == 0 or not best then set("right", 1); set("left", 0); set("up", 0); set("down", 0); set("b1", (f % 12 < 4) and 1 or 0); return end
  local tx, ty = m:read_u16(best + 8), m:read_u16(best + 12)
  local dx, dy = tx - px, ty - py
  if dy > 32768 then dy = dy - 65536 end
  if dx > 32768 then dx = dx - 65536 end
  set("up", dy < -4 and 1 or 0); set("down", dy > 4 and 1 or 0)
  if dx > 36 then set("right", 1); set("left", 0)
  elseif dx < -36 then set("left", 1); set("right", 0)
  else set("right", dx > 0 and (f % 6 < 1) and 1 or 0); set("left", dx <= 0 and (f % 6 < 1) and 1 or 0) end
  set("b1", (f % 12 < 4) and 1 or 0)
end
local nth = 0
emu.register_frame_done(function()
  nth = nth + 1
  if os.getenv("CB_LOAD") and nth == 3 then manager.machine:load(os.getenv("CB_LOAD")) return end
  local f = L.frame()
  if f == 600 then L.F.coin:set_value(1) elseif f == 612 then L.F.coin:set_value(0)
  elseif f == 700 then L.F.start1:set_value(1) elseif f == 712 then L.F.start1:set_value(0) end
  if god == 1 and f > 900 then m:write_u8(0x80113, 0x38) end
  local godlate = (god == 2 and f > 900)
  if f >= 740 and not (m:read_u8(0x80040) & 0x80 == 0) then dobot(f) end
  if assist > 0 then
    for i = 0, 15 do
      local b = 0x81000 + 0x40 * i
      if m:read_u8(b) & 0x80 ~= 0 then
        local key = m:read_u8(b + 2) * 65536 + i
        if born[i] == nil or born[i][1] ~= m:read_u8(b + 2) then born[i] = { m:read_u8(b + 2), f } end
        if f - born[i][2] > assist and (f - born[i][2] - assist) % 25 == 0 then
          m:write_u8(b + 6, m:read_u8(b + 6) | 0x80) -- emulate a light player hit ($f82e writes $80 | strength here): the game's own hit, hurt, death path runs
          if not assisted[i] or assisted[i] ~= born[i][2] then out:write(string.format("A %d slot %d type %d assisted (hit flag +6 poked every 25 frames)\n", f, i, m:read_u8(b + 2))); assisted[i] = born[i][2] end
        end
      else born[i] = nil end
    end
  end
  if portrait then
    for i = 0, 15 do
      local b = 0x81000 + 0x40 * i
      if m:read_u8(b) & 0x80 ~= 0 then
        local key = m:read_u8(b + 2) * 256 + m:read_u8(b + 16)
        local x, y = m:read_u16(b + 8), m:read_u16(b + 12)
        local sx, sy = m:read_u16(0x8040a), m:read_u16(0x80406)
        local nshot = (shots[key] or 0)
        if nshot < portrait and x > sx + 24 and x < sx + 232 and f >= (lastshot[key] or 0) + 100 and m:read_u8(b + 3) >= 6 then
          shots[key] = nshot + 1; lastshot[key] = f
          L.screen:snapshot(string.format("p%05d_t%d_v%d_s%d.png", f, m:read_u8(b + 2), m:read_u8(b + 16), m:read_u8(b + 3)))
          out:write(string.format("S %d type %d var %d state %d sx %d sy %d x %d y %d\n", f, m:read_u8(b + 2), m:read_u8(b + 16), m:read_u8(b + 3), sx, sy, x, y))
        end
      end
    end
  end
  if f >= from then
    out:write(string.format("F %d %04x %04x %02x%02x lvl=%d s400=%02x%02x%02x%02x e=%02x%02x\n", f, m:read_u16(0x8040a), m:read_u16(0x80406), m:read_u8(0x80040), m:read_u8(0x80041), m:read_u8(0x80046), m:read_u8(0x80400), m:read_u8(0x80401), m:read_u8(0x80402), m:read_u8(0x80403), m:read_u8(0x81e02), m:read_u8(0x81e03)))
    out:write(string.format("P %d %s\n", f, hex(0x80100, 0x80)))
    for i = 0, 15 do
      local b = 0x81000 + 0x40 * i
      if m:read_u8(b) & 0x80 ~= 0 then out:write(string.format("R %d %d %s\n", f, i, hex(b, 64))) end
    end
    for i = 0, 7 do
      local b = 0x81c00 + 0x20 * i
      if m:read_u8(b) & 0x80 ~= 0 then out:write(string.format("H %d %d %s\n", f, i, hex(b, 32))) end
    end
  end
  if f >= slo and f <= shi and (f - slo) % sst == 0 then L.screen:snapshot(string.format("e%05d.png", f)) end
  for nm, fr in (os.getenv("CB_SAVES") or ""):gmatch("(%w+):(%d+)") do if f == tonumber(fr) then manager.machine:save(nm) end end
  if godlate then m:write_u8(0x80113, 0x38) end
  if os.getenv("CB_SAVE") and f == tonumber(os.getenv("CB_SAVE_FRAME")) then manager.machine:save(os.getenv("CB_SAVE")) end
  if m:read_u8(0x80040) & 0x10 ~= 0 and not cleared then cleared = f; out:write(string.format("C %d level cleared flag set\n", f)); if f + 90 < stop then stop = f + 90 end end
  if f >= stop then out:close(); manager.machine:exit() end
end)
