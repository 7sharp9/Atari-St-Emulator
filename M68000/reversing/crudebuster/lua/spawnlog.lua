-- spawnlog.lua: log object-record activations and script-pointer movement.
--   per frame: script pointers $81e06 (list A, table $6c000) and $81e0a (list B, table $6d000), scroll words,
--   and every slot whose active bit (record+0 bit 7) went 0 -> 1: the 12 leading bytes and the word at +16.
--   E lines: $81e02/$81e03 (active pool A count, spawn-block flag) whenever they change.
--   CB_PLAN, CB_STOP, CB_OUT (spawnlog.txt)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local sched = os.getenv("CB_PLAN") and dofile(os.getenv("CB_PLAN")) or {}
local stop = tonumber(os.getenv("CB_STOP") or "3000")
local out = io.open((os.getenv("CB_OUT") or ".") .. "/spawnlog.txt", "w")
local m = L.mem
local act, pa, pb, pe = {}, 0, 0, -1
for i = 0, 47 do act[i] = false end
emu.register_frame_done(function()
  local f = L.frame()
  for _, e in ipairs(sched) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  local e = m:read_u16(0x81e02) -- pool A dispatcher: active count (byte) and the spawn-block flag (byte, bit 7)
  if e ~= pe then out:write(string.format("E %d %04x\n", f, e)); pe = e end
  local a, b = m:read_u32(0x81e06), m:read_u32(0x81e0a)
  if a ~= pa or b ~= pb then
    out:write(string.format("P %d A=%x B=%x lvl=%d sx=%04x sy=%04x\n", f, a, b, m:read_u8(0x80046), m:read_u16(0x8040a), m:read_u16(0x80406)))
    pa, pb = a, b
  end
  for i = 0, 47 do
    local base = 0x81000 + 0x40 * i
    local on = (m:read_u8(base) & 0x80) ~= 0
    if on and not act[i] then
      local t = {}
      for k = 0, 0x3f do t[#t + 1] = string.format("%02x", m:read_u8(base + k)) end
      out:write(string.format("S %d slot=%d %s\n", f, i, table.concat(t)))
    end
    act[i] = on
  end
  if f >= stop then out:close(); manager.machine:exit() end
end)
