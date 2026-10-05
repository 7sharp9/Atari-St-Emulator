-- pbp.lua: debugger breakpoints that log (printf; g) with the frame, then run pdrive.lua.
-- Needs FF_MAMEARGS="-debug -debugger none" (ffrun.sh passes it to mame).
--   FF_BPS=<file.lua> returns { {addr_hex, format, args, cond}, ... } e.g. {"1ad8", "D0=%02x ret=%x", "d0&ff,d@(sp)", "d0==3"}
--   FF_BP_OUT=<file>
-- Line: "<frame> B <addr> <formatted>"
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local dbg = manager.machine.debugger
local out = assert(io.open(os.getenv("FF_BP_OUT") or (os.getenv("FF_OUT") .. "/pbp.txt"), "w"))
local bps = dofile(os.getenv("FF_BPS"))
local started, seen = false, 0
emu.register_periodic(function()
  if not started then
    started = true
    for _, b in ipairs(bps) do
      local cond = b[4] or "1"
      local args = (b[3] and b[3] ~= "") and ("," .. b[3]) or ""
      dbg:command(string.format('bpset %s,%s,{printf "B %s %s\\n"%s; g}', b[1], cond, b[1], b[2], args))
    end
    dbg:command("go")
  end
end)
emu.register_frame_done(function()
  local log = dbg.consolelog
  local f = L.frame()
  for i = seen + 1, #log do
    local l = log[i]
    if l:match("^B ") then out:write(string.format("%d %s\n", f, l)) end
  end
  seen = #log
  out:flush()
end)
dofile(os.getenv("PD") .. "/pdrive.lua")
