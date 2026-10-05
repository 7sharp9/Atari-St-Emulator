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
  coin2 = ports[":IN0"].fields["Coin 2"],
  start2 = ports[":IN0"].fields["2 Players Start"],
  up2 = ports[":IN1"].fields["P2 Up"], down2 = ports[":IN1"].fields["P2 Down"],
  left2 = ports[":IN1"].fields["P2 Left"], right2 = ports[":IN1"].fields["P2 Right"],
  b1_2 = ports[":IN1"].fields["P2 Button 1"], b2_2 = ports[":IN1"].fields["P2 Button 2"],
  b3_2 = ports[":IN1"].fields["P2 Button 3"],
}
M.F = F
function M.frame() return M.screen:frame_number() end
function M.ram() -- work RAM as one string
  local t = {}
  local m = M.mem
  for a = 0xff0000, 0xffffff, 2 do
    local v = m:read_u16(a)
    t[#t+1] = string.char(v >> 8, v & 0xff)
  end
  return table.concat(t)
end
function M.region(base, len)
  local t = {}
  for a = base, base + len - 1, 2 do
    local v = M.mem:read_u16(a)
    t[#t+1] = string.char(v >> 8, v & 0xff)
  end
  return table.concat(t)
end
function M.write(path, data) local f = assert(io.open(path, "wb")); f:write(data); f:close() end
-- schedule: list of {frame, fieldname, value}; apply on frame_done so the level is set for the next frame
function M.apply(sched, f)
  for _, e in ipairs(sched) do if e[1] == f then assert(F[e[2]], "unknown field " .. tostring(e[2])); F[e[2]]:set_value(e[3]) end end
end
return M
