-- dumpram.lua: bot-like start (CB_LEVEL), no inputs after start; dump work RAM at frames CB_DUMP "f1,f2,..." to $CB_OUT/ram_<f>.bin
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local want = tonumber(os.getenv("CB_LEVEL") or "0")
local plan = os.getenv("CB_PLAN") and dofile(os.getenv("CB_PLAN")) or {}
local dump = {}; local last = 0
for n in (os.getenv("CB_DUMP") or ""):gmatch("%d+") do dump[tonumber(n)] = true; if tonumber(n) > last then last = tonumber(n) end end
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
  if dump[f] then L.write(string.format("%s/ram_%05d.bin", os.getenv("CB_OUT"), f), L.ram()) end
  if f >= last then manager.machine:exit() end
end)
