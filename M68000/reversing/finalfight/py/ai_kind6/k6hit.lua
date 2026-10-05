-- k6hit.lua (agent D): k6run.lua plus debugger breakpoints that print registers. Run with FF_MAMEARGS="-debug -debugger none".
--   K6_BP="addr|label fmt|expr,expr;addr|..."   -> each hit prints "H <label> <values>" and continues
--   K6_HIT_OUT=<file> receives all H lines (written at exit by wrapping manager.machine:exit)
local dbg = manager.machine.debugger
local out = assert(io.open(os.getenv("K6_HIT_OUT") or "hits.txt", "w"))
local started = false
emu.register_periodic(function()
  if started then return end
  started = true
  for spec in string.gmatch(os.getenv("K6_BP") or "", "[^;]+") do
    local a, fmt, ex = spec:match("^(%x+)|([^|]*)|(.*)$")
    local cmd = string.format('bpset %s,1,{printf "H %s\\n",%s; g}', a, fmt, ex)
    dbg:command(cmd)
  end
  dbg:command("go")
end)
local seen = 0
local function flush()
  local log = dbg.consolelog
  for i = seen + 1, #log do
    if log[i]:match("^H ") then out:write(log[i], "\n") end
  end
  seen = #log
end
emu.register_frame_done(function() flush(); out:flush() end)
dofile(os.getenv("K6_RUN") or (debug.getinfo(1, "S").source:sub(2):match("^(.*)/") .. "/k6run.lua"))
