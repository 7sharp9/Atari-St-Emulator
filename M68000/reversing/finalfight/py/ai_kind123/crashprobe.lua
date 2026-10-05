-- crashprobe.lua: stop at the first execution of $5e88c (reset entry) after the load; print registers, the stack and the previous PCs
local cpu = manager.machine.devices[":maincpu"]
local mem = cpu.spaces["program"]
local dbg = manager.machine.debugger
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local out = assert(io.open(os.getenv("FF_PC_OUT") or "crash.txt", "w"))
local armed = false
emu.register_periodic(function()
  if not armed and L.frame() >= 4200 then
    armed = true
    for _, a in ipairs({"719bc","719c6","719d0","719da","719e4","719ee","719f8","71a02","71a0c","71a16","71a20"}) do dbg:command("bpset " .. a) end
    dbg:command("go")
  end
  if armed and dbg.execution_state == "stop" and not done then
    done = true
    out:write(string.format("stopped at frame %d CURPC=%06x\n", L.frame(), cpu.state["CURPC"].value))
    for _, r in ipairs({"D0","D1","D2","D3","D4","D5","D6","D7","A0","A1","A2","A3","A4","A5","A6","SP","SR","PREVPC"}) do
      local ok, v = pcall(function() return cpu.state[r].value end)
      out:write(string.format("%s=%s\n", r, ok and string.format("%08x", v) or "n/a"))
    end
    local sp = cpu.state["SP"].value
    for i = 0, 24 do out:write(string.format("stack+%02x: %04x\n", i * 2, mem:read_u16(sp + i * 2))) end
    out:flush()
    manager.machine:exit()
  end
end)
dofile(os.getenv("FF_AI123") .. "/fdrive.lua")
