-- hits.lua: count (and log with frame, A1, A3, A6, D7) executions of listed addresses while running fdrive.lua. Needs FF_MAMEARGS="-debug -debugger none".
--   FF_ADDRS="73e2,7388,..." hex; FF_HIT_OUT=<file> (summary), FF_HIT_LOG=<file> (one line per hit: frame addr a1 a3 a6 d7)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local dbg = manager.machine.debugger
local out = assert(io.open(os.getenv("FF_HIT_OUT") or "hits.txt", "w"))
local logf = os.getenv("FF_HIT_LOG") and io.open(os.getenv("FF_HIT_LOG"), "w")
local started = false
local counts, order = {}, {}
emu.register_periodic(function()
  if not started then
    started = true
    for a, r in string.gmatch(os.getenv("FF_ADDRS") or "", "(%x+)@?(%w*)") do
      -- optional @reg: that register is logged in the first value field instead of a1
      local reg = (r ~= "" and r) or "a1"
      dbg:command(string.format('bpset %s,1,{printf "H %s %%x %%x %%x %%x\\n",%s,a3,a6,d7; g}', a, a, reg))
      order[#order + 1] = a
    end
    dbg:command("go")
  end
end)
local seen = 0
emu.register_frame_done(function()
  local f = L.frame()
  local log = dbg.consolelog
  for i = seen + 1, #log do
    local a, a1, a3, a6, d7 = log[i]:match("^H (%x+) (%x+) (%x+) (%x+) (%x+)")
    if a then
      counts[a] = (counts[a] or 0) + 1
      if logf then logf:write(string.format("%d %s %s %s %s %s\n", f, a, a1, a3, a6, d7)) end
    end
  end
  seen = #log
  if f >= tonumber(os.getenv("FF_STOP") or "0") - 1 then
    for _, a in ipairs(order) do out:write(string.format("%s %d\n", a, counts[a] or 0)) end
    out:close(); if logf then logf:close() end
  end
end)
dofile(os.getenv("FF_AI123") .. "/fdrive.lua")
