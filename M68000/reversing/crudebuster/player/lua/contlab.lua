-- contlab.lua: credits / continue / 2-player lab. Inserts CB_COINS coins, starts P1 (frame 700), optionally P2 joins (CB_P2JOIN frame), spawns grunts
-- on the players at CB_SPAWNEVERY frames so they die; when a player enters continue mode (+0 & 3 == 1) and its digit (+126) equals CB_PRESSAT the script
-- presses that player's start button for 12 frames (CB_PRESS=0 to never press: lets the countdown run out). Logs every change of the listed bytes.
--   env: CB_DIR, CB_LEVEL, CB_COINS (default 3), CB_P2JOIN (frame, 0 = no P2), CB_SPAWNEVERY (default 150), CB_PRESSAT (default 5), CB_PRESS (1/0), CB_STOP, CB_OUT (cont.txt)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local coins = tonumber(os.getenv("CB_COINS") or "3")
local p2join = tonumber(os.getenv("CB_P2JOIN") or "0")
local every = tonumber(os.getenv("CB_SPAWNEVERY") or "150")
local pressat = tonumber(os.getenv("CB_PRESSAT") or "5")
local press = (os.getenv("CB_PRESS") or "1") == "1"
local stop = tonumber(os.getenv("CB_STOP") or "9000")
local out = io.open((os.getenv("CB_OUT") or ".") .. "/cont.txt", "w")
local cpu = manager.machine.devices[":maincpu"]
local mem = L.mem
taps = {}
taps[1] = mem:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return ((want << 8) | want) end
end)
local watch = { { "P1mode", 0x80100 }, { "P1life", 0x80114 }, { "P1hp", 0x80113 }, { "P1score3", 0x8013f }, { "P2mode", 0x80180 }, { "P2life", 0x80194 }, { "P2hp", 0x80193 },
  { "credit", 0x80032 }, { "f40", 0x80040 }, { "f5a", 0x8005a }, { "P1d", 0x8017e }, { "timer", 0x80043 }, { "P1+3", 0x80103 }, { "P2+3", 0x80183 } }
local prev = {}
local pressing = {}
local function spawn(px, py)
  for i = 0, 15 do
    local a = 0x81000 + i * 0x40
    if mem:read_u8(a) & 0x80 == 0 then
      mem:write_u8(a, 0x80); mem:write_u8(a + 2, 1); mem:write_u8(a + 16, 1); mem:write_u16(a + 8, px + 50); mem:write_u16(a + 12, py)
      return
    end
  end
end
emu.register_frame_done(function()
  local f = L.frame()
  for c = 0, coins - 1 do
    if f == 600 + 20 * c then L.F.coin:set_value(1) elseif f == 612 + 20 * c then L.F.coin:set_value(0) end
  end
  if f == 700 then L.F.start1:set_value(1) elseif f == 712 then L.F.start1:set_value(0) end
  if p2join > 0 then if f == p2join then L.F.start2:set_value(1) elseif f == p2join + 12 then L.F.start2:set_value(0) end end
  if f >= 960 and f % every == 0 and mem:read_u8(0x80040) & 0x80 ~= 0 then
    for _, p in ipairs({ 0x80100, 0x80180 }) do
      if mem:read_u8(p) & 0x83 == 0x80 and mem:read_u8(p + 90) & 0x40 == 0 then spawn(mem:read_u16(p + 8), mem:read_u16(p + 12)) end
    end
  end
  if press then -- edge-latched start: press 2 of every 5 frames (odd period so both VBL parities are tried) while the continue digit is CB_PRESSAT (an edge is lost when the logic step spans two VBLs, so one press is not enough)
    for pi, p in ipairs({ 0x80100, 0x80180 }) do
      local F = pi == 1 and L.F.start1 or L.F.start2
      if mem:read_u8(p) & 0x83 == 0x81 and mem:read_u8(p + 126) == pressat then F:set_value((f % 5 < 2) and 1 or 0); pressing[pi] = true
      elseif pressing[pi] then F:set_value(0); pressing[pi] = false end
    end
  end
  for _, w in ipairs(watch) do
    local v = mem:read_u8(w[2])
    if prev[w[1]] ~= v then out:write(string.format("%d %s %02x>%02x\n", f, w[1], prev[w[1]] or 0, v)); prev[w[1]] = v end
  end
  if f >= stop then out:close(); manager.machine:exit() end
end)
