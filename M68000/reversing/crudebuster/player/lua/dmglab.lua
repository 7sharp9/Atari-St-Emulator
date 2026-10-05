-- dmglab.lua: damage lab. For each pool A enemy type in CB_TYPES (hex list) spawn one enemy 60 px in front of an idle, vulnerable P1 on level CB_LEVEL,
-- run CB_TRIAL frames and log every write to the player's health byte ($80113) and its writer pc. The player is made idle again between trials.
--   env: CB_DIR, CB_LEVEL (default 0), CB_TYPES "01,02,04,..." (variants default 1; "07:0" = type 7 variant 0), CB_TRIAL (frames, default 260), CB_OUT (dmg.txt, health.txt)
--   dmg.txt   : one line per health write: trial spawned-type variant frame pc old new attacker-type (type byte of the record in A6 at the write, ff = A6 not a pool A record)
--   health.txt: one line per trial: type variant firstwritepc old new
--   optional CB_HITPLAYER=1 : also press button 1 (tap every 20 frames) so the player fights back (used for enemy-hit counts)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local trial = tonumber(os.getenv("CB_TRIAL") or "260")
local types = {}
for t, v in (os.getenv("CB_TYPES") or "01"):gmatch("(%x+):?(%x*)") do types[#types + 1] = { tonumber(t, 16), v ~= "" and tonumber(v, 16) or 1 } end
local out = os.getenv("CB_OUT") or "."
local cpu = manager.machine.devices[":maincpu"]
local mem = L.mem
local cur, t0, state = 0, 0, "wait"
local dmg = io.open(out .. "/dmg.txt", "w")
taps = {}
taps[1] = mem:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return ((want << 8) | want) end
end)
local firstlog = {}
taps[2] = mem:install_write_tap(0x80112, 0x80113, "hp", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0xbbe and pc < 0xbd4 then return end
  if mask & 0xff == 0 then return end
  local ty = types[cur]
  if not ty then return end
  local a6 = cpu.state["A6"].value
  local atype = (a6 >= 0x81000 and a6 < 0x81d00) and mem:read_u8(a6 + 2) or 0xff -- type byte of the record in A6 at the write (the attacker; pool A $81000, B $81400, C $81c00)
  local apool = (a6 >= 0x81c00 and a6 < 0x81d00) and 'C' or (a6 >= 0x81400 and a6 < 0x81c00) and 'B' or (a6 >= 0x81000 and a6 < 0x81400) and 'A' or '-'
  dmg:write(string.format("%d %02x %02x %d %06x %02x %02x %02x %s\n", cur, ty[1], ty[2], L.frame(), pc, mem:read_u8(0x80113), data & 0xff, atype, apool))
end)
local function clearA()
  for i = 0, 15 do local a = 0x81000 + i * 0x40; if mem:read_u8(a) & 0x80 ~= 0 then for k = 0, 0x3f do mem:write_u8(a + k, 0) end end end
end
emu.register_frame_done(function()
  local f = L.frame()
  if f == 600 then L.F.coin:set_value(1) elseif f == 612 then L.F.coin:set_value(0)
  elseif f == 700 then L.F.start1:set_value(1) elseif f == 712 then L.F.start1:set_value(0) end
  if f < 960 then return end
  local p = 0x80100
  local idle = mem:read_u8(p + 4) == 8 and mem:read_u8(p + 5) == 0 and mem:read_u8(p + 1) & 0x20 == 0 and mem:read_u8(p + 3) == 0 and mem:read_u8(p + 90) & 0x40 == 0
  if state == "wait" and idle then
    cur = cur + 1
    if cur > #types then dmg:close(); manager.machine:exit(); return end
    clearA()
    mem:write_u8(p + 19, 0x38); mem:write_u16(p + 54, 0); mem:write_u8(p + 0, mem:read_u8(p) & ~0x10); mem:write_u8(p + 7, 0)
    mem:write_u8(p + 58, 0); mem:write_u8(p + 23, 0)
    local px, py = mem:read_u16(p + 8), mem:read_u16(p + 12)
    local ty = types[cur]
    local a = 0x81000
    mem:write_u8(a, 0x80); mem:write_u8(a + 2, ty[1]); mem:write_u8(a + 16, ty[2]); mem:write_u16(a + 8, px + 60); mem:write_u16(a + 12, py)
    t0 = f; state = "run"
  elseif state == "run" then
    if os.getenv("CB_HITPLAYER") == "1" then L.F.b1:set_value(((f - t0) % 20 == 0) and 1 or 0) end
    if f - t0 >= trial then clearA(); state = "wait"; L.F.b1:set_value(0) end
  end
  if f > 20000 then dmg:close(); manager.machine:exit() end
end)
