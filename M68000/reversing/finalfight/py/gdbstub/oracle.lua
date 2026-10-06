-- Lua oracle: stop at the VBL entry $53e under -debug -debugger none (the callcap mechanism), dump work RAM at hit N.
-- env GD_DUMPS=1,2,10,... GD_OUT=<dir>
local dbg = manager.machine.debugger
local cpu = manager.machine.devices[":maincpu"]
local mem = cpu.spaces["program"]
local out = os.getenv("GD_OUT")
local dumps = {}
local last = 0
for n in string.gmatch(os.getenv("GD_DUMPS"), "%d+") do dumps[tonumber(n)] = true; if tonumber(n) > last then last = tonumber(n) end end
local hits, started = 0, false
local log = assert(io.open(out .. "/lua_log.txt", "w"))
emu.register_periodic(function()
  if not started then
    started = true
    dbg:command("bpset 53e")
    dbg:command("go")
    return
  end
  if dbg.execution_state ~= "stop" or cpu.state["CURPC"].value ~= 0x53e then return end
  hits = hits + 1
  local st = cpu.state
  log:write(string.format("%d a5=%x sp=%x sr=%x frame=%d\n", hits, st["A5"].value, st["SP"].value, st["SR"].value, manager.machine.screens[":screen"]:frame_number()))
  if dumps[hits] then
    local f = assert(io.open(string.format("%s/lua_ram_%d.bin", out, hits), "wb"))
    f:write(mem:read_range(0xff0000, 0xffffff, 8)); f:close()
  end
  if hits >= last then log:close(); manager.machine:exit(); return end
  dbg:command("go")
end)
