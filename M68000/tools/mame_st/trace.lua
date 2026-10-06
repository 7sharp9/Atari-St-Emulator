-- debugger trace of every executed PC from reset; exit after MAMEST_LAST frames
local machine = manager.machine
local screen = machine.screens[":screen"]
local OUT = os.getenv("MAMEST_OUT") or "."
local LAST = tonumber(os.getenv("MAMEST_LAST") or "30")
local dbg = machine.debugger
dbg:command(string.format('trace %s/pc.trace,:m68000,noloop,{tracelog "@%%06X %%04X\\n",curpc,sr}', OUT))
dbg.execution_state = "run"
emu.register_frame_done(function()
  if screen:frame_number() >= LAST then dbg:command("traceflush") machine:exit() end
end)
