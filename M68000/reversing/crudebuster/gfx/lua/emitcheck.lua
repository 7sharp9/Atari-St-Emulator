-- emitcheck.lua: log every sprite-list entry written by the four emitters ($efc0 plain, $f084, $f150, $f21c) together with the inputs
-- the emitter read: part record at A5 (8 bytes), object fields (A6), camera words.  Verified offline by py/emitcheck.py.
--   env as writers.lua; output $CB_OUT/emit.txt, one line per entry:  frame emitter a3 part(8 bytes hex) obj0 obj4 obj7 objx objy camx camy w0 w1 w2 w3
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local out = os.getenv("CB_OUT") or "."
local sched = {}
if os.getenv("CB_PLAN") then sched = dofile(os.getenv("CB_PLAN")) end
local stop = tonumber(os.getenv("CB_STOP") or "3000")
local pokes = {}
for tok in (os.getenv("CB_POKE") or ""):gmatch("[^,]+") do
  local f, a, v, s, o = tok:match("^(%d+):(%x+):(%x+):?(%d*):?([oc]?)$")
  pokes[#pokes + 1] = { tonumber(f), tonumber(a, 16), tonumber(v, 16), tonumber(s ~= "" and s or "1"), o }
end
local cpu = manager.machine.devices[":maincpu"]
local st = cpu.state
local mem = L.mem
local log = assert(io.open(out .. "/emit.txt", "w"))
-- entry write PCs: word0 / word1 / word2 / word3 of each emitter
local emitter = { [0xf034] = 1, [0xf10e] = 2, [0xf1da] = 3, [0xf2a6] = 4 }
local pend = nil
local n = 0
tap_e = mem:install_write_tap(0x82000, 0x83bff, "lists", function(off, data, mask)
  local pc = st["CURPC"].value
  local e = emitter[pc]
  if e then
    local a5 = st["A5"].value; local a6 = st["A6"].value; local a3 = st["A3"].value
    local part = {}
    for i = 0, 7 do part[#part + 1] = string.format("%02x", mem:read_u8(a5 + i)) end
    pend = string.format("%d %d %06x %s %02x %02x %02x %04x %04x %04x %04x %04x", L.frame(), e, a3, table.concat(part), mem:read_u8(a6), mem:read_u8(a6 + 4), mem:read_u8(a6 + 7), mem:read_u16(a6 + 8), mem:read_u16(a6 + 12), mem:read_u16(0x8040a), mem:read_u16(0x80406), data & 0xffff)
    pend_n = 1
  elseif pend and (pc == pend_pc_dummy) then
  elseif pend then
    local w = { [0xf036] = 1, [0xf04c] = 1, [0xf04e] = 1, [0xf110] = 1, [0xf134] = 1, [0xf136] = 1, [0xf1dc] = 1, [0xf200] = 1, [0xf202] = 1, [0xf2a8] = 1, [0xf2cc] = 1, [0xf2ce] = 1 }
    if w[pc] then
      pend = pend .. string.format(" %04x", data & 0xffff)
      pend_n = pend_n + 1
      if pend_n == 4 then log:write(pend, "\n"); pend = nil; n = n + 1 end
    end
  end
end)
emu.register_frame_done(function()
  local f = L.frame()
  for _, e in ipairs(sched) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  for _, p in ipairs(pokes) do
    if p[1] == f then
      for i = 0, p[4] - 1 do
        local b = (p[3] >> (8 * (p[4] - 1 - i))) & 0xff
        if p[5] == "o" then b = b | mem:read_u8(p[2] + i) elseif p[5] == "c" then b = mem:read_u8(p[2] + i) & ~b end
        mem:write_u8(p[2] + i, b)
      end
    end
  end
  if f >= stop then log:close(); manager.machine:exit() end
end)
