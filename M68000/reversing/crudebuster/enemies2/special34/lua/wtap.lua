-- wtap.lua: start level CB_LEVEL (bot optional as in objlog.lua) and log every write into CB_WLO..CB_WHI (hex, inclusive) with the PC.
--   env: CB_DIR, CB_LEVEL, CB_STOP, CB_OUT (wtap.txt), CB_BOT (0/1), CB_HP (1), CB_F0 (first frame logged), CB_WLO, CB_WHI
--   line: <frame> <addr> <data hex> <mask hex> pc=<pc>
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local stop = tonumber(os.getenv("CB_STOP") or "2000")
local f0 = tonumber(os.getenv("CB_F0") or "0")
local bot = tonumber(os.getenv("CB_BOT") or "0")
local lo, hi = tonumber(os.getenv("CB_WLO"), 16), tonumber(os.getenv("CB_WHI"), 16)
local out = io.open((os.getenv("CB_OUT") or ".") .. "/wtap.txt", "w")
local m = L.mem
local cpu = manager.machine.devices[":maincpu"]
taps = {}
taps[1] = m:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return (data & 0xff) ~= data and data or ((want << 8) | want) end
end)
taps[2] = m:install_write_tap(lo, hi, "w", function(off, data, mask)
  local f = L.frame()
  if f >= f0 then out:write(string.format("%d %06x %x %x pc=%06x\n", f, off, data, mask, cpu.state["CURPC"].value)) end
end)
local hp0, atk = nil, 0
local function set(name, v) L.F[name]:set_value(v) end
emu.register_frame_done(function()
  local f = L.frame()
  if f == 600 then set("coin", 1) elseif f == 612 then set("coin", 0)
  elseif f == 700 then set("start1", 1) elseif f == 712 then set("start1", 0) end
  local px, py = m:read_u16(0x80108), m:read_u16(0x8010c)
  local hp = m:read_u8(0x80113)
  local running = (m:read_u8(0x80040) & 0x80) ~= 0 and f > 720
  if running and hp0 == nil and hp > 0 then hp0 = hp end
  if running and hp0 and tonumber(os.getenv("CB_HP") or "1") == 1 then m:write_u8(0x80113, hp0) end
  if bot == 1 and running then
    local best, bd = nil, 1e9
    for i = 0, 15 do
      local base = 0x81000 + 0x40 * i
      if (m:read_u8(base) & 0x80) ~= 0 then
        local ex, ey = m:read_u16(base + 8), m:read_u16(base + 12)
        local d = math.abs(ex - px) + 3 * math.abs(ey - py)
        if d < bd then best, bd = { ex, ey }, d end
      end
    end
    local l, r, u, d, hit = 0, 0, 0, 0, 0
    if best and bd < 400 then
      local dx, dy = best[1] - px, best[2] - py
      if dy < -4 then u = 1 elseif dy > 4 then d = 1 end
      if dx > 36 then r = 1 elseif dx < -36 then l = 1 end
      if math.abs(dx) < 56 and math.abs(dy) < 14 then
        if dx > 0 then r = 1 else l = 1 end
        atk = (atk + 1) % 8; hit = atk < 4 and 1 or 0
      end
    else r = 1 end
    set("right", r); set("left", l); set("up", u); set("down", d); set("b1", hit)
  end
  if f >= stop then out:close(); manager.machine:exit() end
end)
