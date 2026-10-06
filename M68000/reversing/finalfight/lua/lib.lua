-- shared helpers for agentB scripts
local M = {}
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
M.mem = cpu.spaces["program"]
M.screen = machine.screens[":screen"]
local ports = machine.ioport.ports
local F = {
  coin = ports[":IN0"].fields["Coin 1"],
  start1 = ports[":IN0"].fields["1 Player Start"],
  up = ports[":IN1"].fields["P1 Up"], down = ports[":IN1"].fields["P1 Down"],
  left = ports[":IN1"].fields["P1 Left"], right = ports[":IN1"].fields["P1 Right"],
  b1 = ports[":IN1"].fields["P1 Button 1"], b2 = ports[":IN1"].fields["P1 Button 2"],
  b3 = ports[":IN1"].fields["P1 Button 3"],
}
M.F = F
function M.frame() return M.screen:frame_number() end
-- read_range returns the bytes in bus order in one call: equal to the old per-word loop (work RAM 65,536 of 65,536 bytes, gfx RAM 196,608 of 196,608 on bb_10560), about 100x faster (README "Lua cost")
function M.region(base, len)
  len = len + (len & 1) -- the word loop this replaced always returned whole words
  return M.mem:read_range(base, base + len - 1, 8)
end
function M.ram() -- work RAM as one string
  return M.region(0xff0000, 0x10000)
end
function M.write(path, data) local f = assert(io.open(path, "wb")); f:write(data); f:close() end
-- schedule: list of {frame, fieldname, value}; apply on frame_done so the level is set for the next frame
function M.apply(sched, f)
  for _, e in ipairs(sched) do if e[1] == f then F[e[2]]:set_value(e[3]) end end
end
return M
