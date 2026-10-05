-- bot_bp.lua: bot2p.lua plus debugger breakpoints that print to the console log (run with FF_MAMEARGS="-debug -debugger none").
--   FFD_BPS = file returning { {addr_hex, "printf format and args"}, ... }  (each becomes bpset addr,1,{printf ...; g})
--   FFD_BPOUT = output file (each console line starting with "B " is copied with the frame number prepended)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local dbg = manager.machine.debugger
local bps = dofile(os.getenv("FFD_BPS"))
local out = assert(io.open(os.getenv("FFD_BPOUT"), "w"))
local started, seen = false, 0
emu.register_periodic(function()
  if not started then
    started = true
    for _, b in ipairs(bps) do dbg:command(string.format('bpset %s,1,{printf "B %s\\n"%s; g}', b[1], b[3] or b[1], b[2] and (", " .. b[2]) or "")) end
    dbg:command("go")
  end
end)
emu.register_frame_done(function()
  local log = dbg.consolelog
  local f = L.frame()
  for i = seen + 1, #log do
    local l = log[i]
    if l:match("^B ") then out:write(f .. " " .. l .. "\n") elseif os.getenv("FFD_BPALL") then out:write(f .. " ? " .. l .. "\n") end
  end
  seen = #log
  out:flush()
end)
dofile(os.getenv("FF_DIR") .. "/bot2p.lua")
