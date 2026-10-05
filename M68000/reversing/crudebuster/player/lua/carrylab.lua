-- carrylab.lua: carry lab for pool B props. For each pool B type in CB_TYPES (hex) spawn the prop 24 px in front of an invulnerable, idle P1, then
--   t=20 tap b3 (grab), t=70 tap b1 (attack while carrying), t=120 tap b3 (throw); log the player's +26 (carry flags) +27 +58 +92 and the prop's state each stage.
--   env: CB_DIR, CB_LEVEL, CB_TYPES "08,09,17,..." (variant 0; "08:1"), CB_DIST (24), CB_OUT (carry.txt: trial type stage frame +26 +27 +24 +25 +58 prop+3 prop+4 prop+0)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local dist = tonumber(os.getenv("CB_DIST") or "24")
local types = {}
for t, v in (os.getenv("CB_TYPES") or "08"):gmatch("(%x+):?(%x*)") do types[#types + 1] = { tonumber(t, 16), v ~= "" and tonumber(v, 16) or 0 } end
local out = io.open((os.getenv("CB_OUT") or ".") .. "/carry.txt", "w")
local cpu = manager.machine.devices[":maincpu"]
local mem = L.mem
taps = {}
taps[1] = mem:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return ((want << 8) | want) end
end)
local cur, t0, state = 0, 0, "wait"
local function clearB() for i = 0, 31 do local a = 0x81400 + i * 0x40; if mem:read_u8(a) & 0x80 ~= 0 then for k = 0, 0x3f do mem:write_u8(a + k, 0) end end end end
local function clearA() for i = 0, 15 do local a = 0x81000 + i * 0x40; if mem:read_u8(a) & 0x80 ~= 0 then for k = 0, 0x3f do mem:write_u8(a + k, 0) end end end end
local function snap(stage, f)
  local p = 0x80100
  local a = 0x81400
  out:write(string.format("%d %02x %s %d %02x %02x %02x %02x %02x %02x %02x %02x\n", cur, types[cur][1], stage, f - t0, mem:read_u8(p + 26), mem:read_u8(p + 27), mem:read_u8(p + 24), mem:read_u8(p + 25),
    mem:read_u8(p + 58), mem:read_u8(a + 3), mem:read_u8(a + 4), mem:read_u8(a)))
end
emu.register_frame_done(function()
  local f = L.frame()
  if f == 600 then L.F.coin:set_value(1) elseif f == 612 then L.F.coin:set_value(0)
  elseif f == 700 then L.F.start1:set_value(1) elseif f == 712 then L.F.start1:set_value(0) end
  if f < 960 then return end
  local p = 0x80100
  mem:write_u8(p + 19, 0x38); mem:write_u16(p + 54, 0x7fff)
  local idle = mem:read_u8(p + 4) == 8 and mem:read_u8(p + 5) == 0 and mem:read_u8(p + 1) & 0x20 == 0 and mem:read_u8(p + 3) == 0 and mem:read_u8(p + 90) & 0x40 == 0 and mem:read_u8(p + 26) == 0
  if state == "wait" and idle then
    cur = cur + 1
    if cur > #types then out:close(); manager.machine:exit(); return end
    clearA(); clearB()
    mem:write_u8(p + 7, 0)
    local px, py = mem:read_u16(p + 8), mem:read_u16(p + 12)
    local ty = types[cur]
    local a = 0x81400
    mem:write_u8(a, 0x80); mem:write_u8(a + 2, ty[1]); mem:write_u8(a + 16, ty[2]); mem:write_u16(a + 8, px + dist); mem:write_u16(a + 12, py)
    t0 = f; state = "run"
  elseif state == "run" then
    local d = f - t0
    L.F.b3:set_value((d == 20 or d == 120) and 1 or 0); L.F.b1:set_value((d == 70) and 1 or 0)
    if d == 19 then snap("pre", f) elseif d == 65 then snap("held", f) elseif d == 100 then snap("afteratk", f) elseif d == 118 then snap("prethrow", f) elseif d == 180 then snap("end", f) end
    if d >= 190 then clearB(); L.F.b3:set_value(0); L.F.b1:set_value(0); state = "wait" end
  end
  if f > 30000 then out:close(); manager.machine:exit() end
end)
