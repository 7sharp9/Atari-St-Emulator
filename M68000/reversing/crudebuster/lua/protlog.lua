-- protlog.lua: log every 68000 access to the protection port $bc004-$bc005 (frame, pc, r/w, offset, data)
--   and the writes to the layer-control chips $b5000-$b600f. CB_PLAN, CB_STOP, CB_OUT (protlog.txt)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local sched = os.getenv("CB_PLAN") and dofile(os.getenv("CB_PLAN")) or {}
local stop = tonumber(os.getenv("CB_STOP") or "3000")
local out = io.open((os.getenv("CB_OUT") or ".") .. "/protlog.txt", "w")
local cpu = manager.machine.devices[":maincpu"]
local m = L.mem
taps = {}
taps[#taps + 1] = m:install_write_tap(0xbc004, 0xbc005, "pw", function(off, data, mask)
  out:write(string.format("%d W %06x pc=%06x off=%d data=%04x mask=%04x\n", L.frame(), 0xbc004 + off, cpu.state["CURPC"].value, off, data, mask))
end)
taps[#taps + 1] = m:install_read_tap(0xbc004, 0xbc005, "pr", function(off, data, mask)
  out:write(string.format("%d R %06x pc=%06x off=%d data=%04x mask=%04x\n", L.frame(), 0xbc004 + off, cpu.state["CURPC"].value, off, data, mask))
end)
emu.register_frame_done(function()
  local f = L.frame()
  for _, e in ipairs(sched) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  if f >= stop then out:close(); manager.machine:exit() end
end)
