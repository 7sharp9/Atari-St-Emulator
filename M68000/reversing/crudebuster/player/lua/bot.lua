-- bot.lua: play Crude Buster level CB_LEVEL (0..5) as P1 with a simple event-driven policy; reusable by the other agents.
--   Starts the game like startlevel.lua (coin at 600, start at 700, level byte replaced). From CB_FROM (default 900, after the wall-crash
--   entrance) the bot reads the RAM every frame and presses buttons: walk right; when a live pool A enemy is within CB_RANGE pixels
--   face it and tap button 1 (jab chain); optionally poke the health cell so the player cannot die (CB_GOD=1, default).
-- env:
--   CB_DIR      reversing/crudebuster/lua (lib.lua)
--   CB_LEVEL    0..5 (default 0)             CB_STOP    last frame (default 6000)
--   CB_OUT      output dir (bot.csv, events.txt)       CB_LOG  frames between csv rows (default 10)
--   CB_GOD      1: poke health $80113 = $38 and the invulnerability timer $80136 = $7fff every frame (default 1); 0 to let it die
--   CB_SAVEAT   "frame:name,frame:name"  save a MAME state (into $CB_RUN/sta/cbuster/<name>.sta) at the end of that frame
--   CB_STOPAT   "x:NNNN"  hex scroll counter ($8040a) at which to stop (saves "bot_end" first)       CB_LOAD  state name to load at frame 1 (then CB_FROM applies)
--   CB_FROM     first frame the policy acts (default 900)      CB_RANGE  attack reach in px (default 36)
--   CB_SHOTS    "lo:hi:step" screenshots into $CB_RUN/snap/cbuster/bNNNNN.png
--   CB_NOSOLID  1: clear the solid bit (bit 2 of byte 0) of pool B slots 24..31 every frame, so breakable walls do not block the walk
--   CB_NOATTACK 1: only walk (no button 1)       CB_PLAYER2 1: also start P2 (coin+start2) and make P2 mirror P1's presses (2-player tests)
-- The policy is deliberately dumb (no pickups, no dodging); it is a driver, not a player model. Positions: x = word at +8, y = word at +12 of the record.
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local stop = tonumber(os.getenv("CB_STOP") or "6000")
local from = tonumber(os.getenv("CB_FROM") or "900")
local range = tonumber(os.getenv("CB_RANGE") or "36")
local logn = tonumber(os.getenv("CB_LOG") or "10")
local god = (os.getenv("CB_GOD") or "1") == "1"
local noattack = os.getenv("CB_NOATTACK") == "1"
local nosolid = os.getenv("CB_NOSOLID") == "1"
local two = os.getenv("CB_PLAYER2") == "1"
local out = os.getenv("CB_OUT") or "."
local saveat = {}
for f, n in (os.getenv("CB_SAVEAT") or ""):gmatch("(%d+):([%w_]+)") do saveat[tonumber(f)] = n end
local stopx = os.getenv("CB_STOPAT") and tonumber(os.getenv("CB_STOPAT"):match("x:(%x+)"), 16)
local slo, shi, sst = 0, -1, 1
if os.getenv("CB_SHOTS") then slo, shi, sst = os.getenv("CB_SHOTS"):match("(%d+):(%d+):(%d+)"); slo, shi, sst = tonumber(slo), tonumber(shi), tonumber(sst) end
local cpu = manager.machine.devices[":maincpu"]
local mem = L.mem
taps = {}
taps[1] = mem:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return ((want << 8) | want) end
end)
local csv = io.open(out .. "/bot.csv", "w")
csv:write("frame,px,py,face,act,sub,pstate,hp,lives,score,scrollx,scrolly,nenemy,lvl,flags40\n")
local ev = io.open(out .. "/events.txt", "w")
local loaded = false
local tapphase = 0
local function bcd(v) return tonumber(string.format("%x", v)) or 0 end
local function enemies()
  local t = {}
  for i = 0, 15 do
    local a = 0x81000 + i * 0x40
    if mem:read_u8(a) & 0x80 ~= 0 then
      t[#t + 1] = { a = a, type = mem:read_u8(a + 2), state = mem:read_u8(a + 3), x = mem:read_u16(a + 8), y = mem:read_u16(a + 12), hp = mem:read_u8(a + 5) }
    end
  end
  return t
end
local function press(F, on) F:set_value(on and 1 or 0) end
emu.register_frame_done(function()
  local f = L.frame()
  if os.getenv("CB_LOAD") and not loaded then loaded = true; manager.machine:load(os.getenv("CB_LOAD")); return end
  if not os.getenv("CB_LOAD") then
    if f == 600 then L.F.coin:set_value(1) elseif f == 612 then L.F.coin:set_value(0)
    elseif f == 700 then L.F.start1:set_value(1) elseif f == 712 then L.F.start1:set_value(0)
    end
    if two then
      if f == 650 then L.F.coin:set_value(1) elseif f == 662 then L.F.coin:set_value(0)
      elseif f == 702 then L.F.start2:set_value(1) elseif f == 714 then L.F.start2:set_value(0) end
    end
  end
  local running = mem:read_u8(0x80040) & 0x80 ~= 0
  if running and f >= from then
    local p = 0x80100
    local px, py, face = mem:read_u16(p + 8), mem:read_u16(p + 12), mem:read_u8(p + 7)
    local intro = mem:read_u8(p + 3) ~= 0 or mem:read_u8(p + 0) & 0x80 == 0 or mem:read_u8(p + 90) & 0x40 ~= 0 or mem:read_u8(0x80041) & 1 ~= 0
    if god then mem:write_u8(p + 19, 0x38); mem:write_u16(p + 54, 0x7fff) end
    if nosolid then -- pool B slots 24..31 with bit 2 of byte 0 set are solid blocks ($ec34): clear the bit so walls (the rubble in level 1) do not stop the walk
      for i = 24, 31 do local a = 0x81400 + i * 0x40; local b = mem:read_u8(a); if b & 0x84 == 0x84 then mem:write_u8(a, b & ~4) end end
    end
    local E = enemies()
    local best, bd = nil, 1e9
    for _, e in ipairs(E) do
      local dx = e.x - px
      local d = math.abs(dx) + 2 * math.abs(e.y - py)
      if e.state ~= 2 and e.state ~= 4 and e.state ~= 5 and d < bd and math.abs(e.y - py) < 0x60 then best, bd = e, d end
    end
    local right, left, up, down, b1 = false, false, false, false, false
    if not intro then
      if best then
        local dx = best.x - px
        if math.abs(dx) > range then right, left = dx > 0, dx < 0
        else
          if (dx > 0) ~= (face == 0) then right, left = dx > 0, dx < 0 end -- turn toward it
          if best.y - py > 8 then down = true elseif py - best.y > 8 then up = true end
          tapphase = tapphase + 1
          if not noattack and tapphase % 5 == 0 then b1 = true end
        end
      else
        right = true
      end
    end
    press(L.F.right, right); press(L.F.left, left); press(L.F.up, up); press(L.F.down, down); press(L.F.b1, b1)
    if two then
      press(L.F.p2right, right); press(L.F.p2left, left); press(L.F.p2up, up); press(L.F.p2down, down); press(L.F.p2b1, b1)
    end
    if f % logn == 0 then
      csv:write(string.format("%d,%d,%d,%d,%d,%d,%d,%d,%d,%08x,%x,%x,%d,%d,%02x\n", f, px, py, face, mem:read_u8(p + 4), mem:read_u8(p + 5), mem:read_u8(p + 3),
        mem:read_u8(p + 19), mem:read_u8(p + 20), mem:read_u32(p + 60), mem:read_u16(0x8040a), mem:read_u16(0x80406), #E, mem:read_u8(0x80046), mem:read_u8(0x80040)))
    end
  end
  if f >= slo and f <= shi and (f - slo) % sst == 0 then L.screen:snapshot(string.format("b%05d.png", f)) end
  if saveat[f] then manager.machine:save(saveat[f]); ev:write(string.format("%d saved %s\n", f, saveat[f])) end
  if stopx and running and f >= from and mem:read_u16(0x8040a) >= stopx then manager.machine:save("bot_end"); ev:write(string.format("%d stopat reached scrollx=%x\n", f, mem:read_u16(0x8040a))); stop = f end
  if f >= stop then csv:close(); ev:close(); manager.machine:exit() end
end)
