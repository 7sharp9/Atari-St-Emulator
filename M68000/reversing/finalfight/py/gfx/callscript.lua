-- callscript.lua: run a list of commands against the game, calling its own routines (like framecap.lua, generalised).
-- Run: FF_MAMEARGS="-debug -debugger none" CS_IN=cmds.txt CS_OUT=out.txt ffrun.sh callscript.lua 600
-- Commands (one per line, numbers hex):
--   P addr width value      poke (width 1, 2 or 4)
--   Z addr len              zero len bytes
--   S REG value             set a CPU register (D0-D7, A0-A6)
--   C addr                  call the routine at addr (SR=$2700, sentinel return); registers persist between calls
--   R addr len              read len bytes, written to the output as "R addr hexbytes"
--   M text                  copy text to the output
-- The game is parked at its VBL entry $53e first (registers can only be set there, lua/callcap.lua) and never resumes.
local cpu = manager.machine.devices[":maincpu"]
local mem = cpu.spaces["program"]
local dbg = manager.machine.debugger
assert(dbg, "run with FF_MAMEARGS=\"-debug -debugger none\"")
local cmds = {}
for line in io.lines(assert(os.getenv("CS_IN"))) do
  local t = {}
  for tok in line:gmatch("%S+") do t[#t + 1] = tok end
  if #t > 0 then cmds[#cmds + 1] = t end
end
local out = assert(io.open(assert(os.getenv("CS_OUT")), "w"))
local SENTINEL = 0x0fff00
local pc_i, frames, armed, started, finished, calling = 1, 0, false, false, false, false

local function hex(n) return tonumber(n, 16) end

-- run commands until the next C (which needs the debugger to run) or the end
local function pump()
  while pc_i <= #cmds do
    local c = cmds[pc_i]
    pc_i = pc_i + 1
    local op = c[1]
    if op == "P" then
      local a, w, v = hex(c[2]), hex(c[3]), hex(c[4])
      if w == 1 then mem:write_u8(a, v) elseif w == 2 then mem:write_u16(a, v) else mem:write_u32(a, v) end
    elseif op == "Z" then
      local a, n = hex(c[2]), hex(c[3])
      for i = 0, n - 1 do mem:write_u8(a + i, 0) end
    elseif op == "S" then
      cpu.state[c[2]].value = hex(c[3])
    elseif op == "R" then
      local a, n = hex(c[2]), hex(c[3])
      local t = {}
      for i = 0, n - 2, 2 do t[#t + 1] = string.format("%04x", mem:read_u16(a + i)) end
      out:write(string.format("R %x ", a), table.concat(t), "\n")
    elseif op == "M" then
      out:write(table.concat(c, " ", 2), "\n")
    elseif op == "C" then
      local sp = 0xff0f00
      mem:write_u32(sp, SENTINEL)
      cpu.state["SP"].value = sp
      cpu.state["SR"].value = 0x2700
      cpu.state["PC"].value = hex(c[2])
      calling = true
      dbg:command("go")
      return
    end
  end
  finished = true
  out:close()
  manager.machine:exit()
end

emu.register_periodic(function()
  if finished then return end
  frames = frames + 1
  if not started then
    started = true
    dbg:command("bpset 53e")
    dbg:command("go")
    return
  end
  if dbg.execution_state ~= "stop" then return end
  local pc = cpu.state["CURPC"].value
  if not armed then
    if pc == 0x53e and frames > 90 then
      armed = true
      dbg:command("bpclear")
      dbg:command("bpset " .. string.format("%x", SENTINEL))
      pump()
    elseif pc == 0x53e then
      dbg:command("go")
    end
    return
  end
  if calling and pc == SENTINEL then
    calling = false
    pump()
  end
end)
