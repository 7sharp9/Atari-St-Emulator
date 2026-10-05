-- sndbp.lua: breakpoint log of the sound queue entry $9f8 (every queued command: D0 = id, the return address on the stack) while stagebot.lua plays (needs -debug).
-- Environment: SB_OUT log file; FF_* as stagebot.lua. Lines "f=<frame> id=<d0> ret=<(sp)> a6=<A6>".
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local dbg = manager.machine.debugger
local out = assert(io.open(os.getenv("SB_OUT"), "w"))
local started, seen = false, 0
emu.register_periodic(function()
  if not started then
    started = true
    for a in string.gmatch(os.getenv("SB_ADDRS") or "9f8", "(%x+)") do
      dbg:command(string.format('bpset %s,1,{printf "H %s %%x %%x %%x\\n",d0&ffff,d@(usp),a6&ffffff; g}', a, a))
    end
    dbg:command("go")
  end
end)
emu.register_frame_done(function()
  local f = L.frame()
  local log = dbg.consolelog
  for i = seen + 1, #log do
    local a, d0, ret, a6 = log[i]:match("^H (%x+) (%x+) (%x+) (%x+)")
    if a then out:write(string.format("f=%d bp=%s id=%s ret=%s a6=%s\n", f, a, d0, ret, a6)) end
  end
  seen = #log
  if f % 600 == 0 then out:flush() end
end)
dofile(os.getenv("FF_DIR") .. "/stagebot.lua")
