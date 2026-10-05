-- shared helpers for the Crude Buster scripts (MAME set cbuster, 68000 work RAM $080000-$083fff)
local M = {}
local machine = manager.machine
M.mem = machine.devices[":maincpu"].spaces["program"]
M.screen = machine.screens[":screen"]
local ports = machine.ioport.ports
M.F = {
  coin = ports[":COINS"].fields["Coin 1"],
  start1 = ports[":P1_P2"].fields["1 Player Start"], start2 = ports[":P1_P2"].fields["2 Players Start"],
  up = ports[":P1_P2"].fields["P1 Up"], down = ports[":P1_P2"].fields["P1 Down"],
  left = ports[":P1_P2"].fields["P1 Left"], right = ports[":P1_P2"].fields["P1 Right"],
  b1 = ports[":P1_P2"].fields["P1 Button 1"], b2 = ports[":P1_P2"].fields["P1 Button 2"],
  b3 = ports[":P1_P2"].fields["P1 Button 3"],
  p2up = ports[":P1_P2"].fields["P2 Up"], p2down = ports[":P1_P2"].fields["P2 Down"],
  p2left = ports[":P1_P2"].fields["P2 Left"], p2right = ports[":P1_P2"].fields["P2 Right"],
  p2b1 = ports[":P1_P2"].fields["P2 Button 1"], p2b2 = ports[":P1_P2"].fields["P2 Button 2"],
  p2b3 = ports[":P1_P2"].fields["P2 Button 3"],
}
function M.frame() return M.screen:frame_number() end
function M.region(base, len) -- bytes as a string
  local t = {}
  for a = base, base + len - 1, 2 do
    local v = M.mem:read_u16(a)
    t[#t + 1] = string.char(v >> 8, v & 0xff)
  end
  return table.concat(t)
end
function M.ram() return M.region(0x80000, 0x4000) end
function M.write(path, data) local f = assert(io.open(path, "wb")); f:write(data); f:close() end
return M
