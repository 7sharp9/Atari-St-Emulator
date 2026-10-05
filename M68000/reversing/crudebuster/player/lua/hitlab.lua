-- hitlab.lua: hit lab. For each pool A type in CB_TYPES spawn one enemy CB_DIST px in front of an invulnerable P1 (health and timer poked every frame), the player
-- taps button 1 (CB_TAP frames period) facing it, and the script logs every change of the enemy's health (+5), state (+3), hit byte (+6) and the player's score.
--   env: CB_DIR, CB_LEVEL, CB_TYPES "01:1,00:0,...", CB_TRIAL (frames, default 300), CB_DIST (default 36), CB_TAP (default 5), CB_OUT (hit.txt: trial type frame field old>new)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local trial = tonumber(os.getenv("CB_TRIAL") or "300")
local dist = tonumber(os.getenv("CB_DIST") or "36")
local tap = tonumber(os.getenv("CB_TAP") or "5")
local btn = os.getenv("CB_BTN") or "b1" -- button that is tapped (b3 = grab, then throw on the next tap)
local types = {}
for t, v in (os.getenv("CB_TYPES") or "01"):gmatch("(%x+):?(%x*)") do types[#types + 1] = { tonumber(t, 16), v ~= "" and tonumber(v, 16) or 1 } end
local out = io.open((os.getenv("CB_OUT") or ".") .. "/hit.txt", "w")
local cpu = manager.machine.devices[":maincpu"]
local mem = L.mem
taps = {}
taps[1] = mem:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return ((want << 8) | want) end
end)
local cur, t0, state, prev = 0, 0, "wait", {}
local function clearA() for i = 0, 15 do local a = 0x81000 + i * 0x40; if mem:read_u8(a) & 0x80 ~= 0 then for k = 0, 0x3f do mem:write_u8(a + k, 0) end end end end
emu.register_frame_done(function()
  local f = L.frame()
  if f == 600 then L.F.coin:set_value(1) elseif f == 612 then L.F.coin:set_value(0)
  elseif f == 700 then L.F.start1:set_value(1) elseif f == 712 then L.F.start1:set_value(0) end
  if f < 960 then return end
  local p = 0x80100
  mem:write_u8(p + 19, 0x38); mem:write_u16(p + 54, 0x7fff)
  local idle = mem:read_u8(p + 4) == 8 and mem:read_u8(p + 5) == 0 and mem:read_u8(p + 1) & 0x20 == 0 and mem:read_u8(p + 3) == 0 and mem:read_u8(p + 90) & 0x40 == 0
  if state == "wait" and idle then
    cur = cur + 1
    if cur > #types then out:close(); manager.machine:exit(); return end
    clearA()
    mem:write_u8(p + 7, 0)
    local px, py = mem:read_u16(p + 8), mem:read_u16(p + 12)
    local ty = types[cur]
    local a = 0x81000
    mem:write_u8(a, 0x80); mem:write_u8(a + 2, ty[1]); mem:write_u8(a + 16, ty[2]); mem:write_u16(a + 8, px + dist); mem:write_u16(a + 12, py)
    t0 = f; state = "run"; prev = {}
  elseif state == "run" then
    local a = 0x81000
    L.F[btn]:set_value(((f - t0) % tap == 0) and 1 or 0)
    local cur_ = { hp = mem:read_u8(a + 5), st = mem:read_u8(a + 3), hit = mem:read_u8(a + 6), act = mem:read_u8(a) & 0x80, sc = mem:read_u32(p + 60), x = mem:read_u16(a + 8), pf = mem:read_u8(p + 26), p27 = mem:read_u8(p + 27), h17 = mem:read_u8(a + 17), ex = nil }
    cur_.ex = nil
    for k, v in pairs(cur_) do
      if prev[k] ~= v then out:write(string.format("%d %02x %d %s %x>%x\n", cur, types[cur][1], f - t0, k, prev[k] or 0, v)); prev[k] = v end
    end
    if f - t0 >= trial then clearA(); L.F[btn]:set_value(0); state = "wait" end
  end
  if f > 25000 then out:close(); manager.machine:exit() end
end)
