-- shots.lua: like reclog.lua but screenshots only: CB_SHOTS "lo:hi:step" -> $CB_RUN/snap/
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local plan = os.getenv("CB_PLAN") and dofile(os.getenv("CB_PLAN")) or {}
local stop = tonumber(os.getenv("CB_STOP") or "2000")
local slo, shi, sst = os.getenv("CB_SHOTS"):match("(%d+):(%d+):(%d+)"); slo, shi, sst = tonumber(slo), tonumber(shi), tonumber(sst)
local cpu = manager.machine.devices[":maincpu"]
taps = {}
taps[1] = L.mem:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc >= 0x1400 and pc < 0x1480 then return ((want << 8) | want) end
end)
emu.register_frame_done(function()
  local f = L.frame()
  if f == 600 then L.F.coin:set_value(1) elseif f == 612 then L.F.coin:set_value(0)
  elseif f == 700 then L.F.start1:set_value(1) elseif f == 712 then L.F.start1:set_value(0) end
  for _, e in ipairs(plan) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  if f >= slo and f <= shi and (f - slo) % sst == 0 then L.screen:snapshot(string.format("s%05d.png", f)) end
  if f >= stop then manager.machine:exit() end
end)
