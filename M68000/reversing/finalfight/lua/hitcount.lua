-- hitcount.lua: count executions of listed addresses per run with debugger breakpoints (action "printf; g").
-- Run with -debug -debugger none (ffrun_a.sh with FF_MAMEARGS="-debug -debugger none").
--   FF_ADDRS="5764,5acdc,..."  hex addresses;  FF_HIT_OUT=<file>;  FF_LOAD / FF_STOP as in ffdrive.lua
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local dbg = manager.machine.debugger
local out = assert(io.open(os.getenv("FF_HIT_OUT") or "hits.txt", "w"))
local started = false
local counts, order = {}, {}
emu.register_periodic(function()
  if not started then
    started = true
    for a in string.gmatch(os.getenv("FF_ADDRS") or "", "(%x+)") do
      dbg:command(string.format('bpset %s,1,{printf "H %s\\n"; g}', a, a))
      order[#order + 1] = a
    end
    dbg:command("go")
  end
end)
local seen = 0
emu.register_frame_done(function()
  local f = L.frame()
  local wlo = tonumber(os.getenv("FF_WALK_LO") or "0")
  if wlo > 0 then L.F.right:set_value(f >= wlo and 1 or 0) end
  local log = dbg.consolelog
  local n = 0
  for i = seen + 1, #log do
    local l = log[i]
    local a = l:match("^H (%x+)")
    if a then counts[a] = (counts[a] or 0) + 1; n = n + 1 end
  end
  seen = #log
  if f % 100 == 0 then print("frame", f, "hits so far", n) end
  if f >= tonumber(os.getenv("FF_STOP") or "2300") then
    for _, a in ipairs(order) do out:write(string.format("%s %d\n", a, counts[a] or 0)) end
    out:close()
  end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
