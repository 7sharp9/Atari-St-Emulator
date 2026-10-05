-- startlevel.lua: coin, start, and force the level number: the write at $146e (move.b #0,$80046, game start) is replaced by CB_LEVEL.
--   CB_DIR, CB_LEVEL (0-5), CB_STOP, CB_SHOTS "lo:hi:step", CB_SAVE/CB_SAVE_FRAME (state name / frame), CB_PLAN (extra inputs after start)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local plan = os.getenv("CB_PLAN") and dofile(os.getenv("CB_PLAN")) or {}
local stop = tonumber(os.getenv("CB_STOP") or "2000")
local slo, shi, sst = 0, -1, 1
if os.getenv("CB_SHOTS") then slo, shi, sst = os.getenv("CB_SHOTS"):match("(%d+):(%d+):(%d+)"); slo, shi, sst = tonumber(slo), tonumber(shi), tonumber(sst) end
local cpu = manager.machine.devices[":maincpu"]
taps = {}
taps[1] = L.mem:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  if cpu.state["CURPC"].value == 0x146e + 6 or cpu.state["CURPC"].value >= 0x1400 and cpu.state["CURPC"].value < 0x1480 then
    return (data & 0xff) ~= data and data or ((want << 8) | want)
  end
end)
emu.register_frame_done(function()
  local f = L.frame()
  if f == 600 then L.F.coin:set_value(1) elseif f == 612 then L.F.coin:set_value(0)
  elseif f == 700 then L.F.start1:set_value(1) elseif f == 712 then L.F.start1:set_value(0) end
  for _, e in ipairs(plan) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  if f >= slo and f <= shi and (f - slo) % sst == 0 then L.screen:snapshot(string.format("l%05d.png", f)) end
  if os.getenv("CB_SAVE") and f == tonumber(os.getenv("CB_SAVE_FRAME")) then manager.machine:save(os.getenv("CB_SAVE")) end
  if f >= stop then io.stderr:write(string.format("level byte %d\n", L.mem:read_u8(0x80046))); manager.machine:exit() end
end)
