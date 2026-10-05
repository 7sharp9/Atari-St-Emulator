-- z80sweep.lua: pass-5 agent B. A sound lab: cold boot to frame SW_START (default 300), then free every task slot except the idle task 11 (so nothing but the VBL sound pump $984 and our ring entries
-- reach the Z80), and inject the sound ids of SW_IDS (hex, comma list; default 00-3f,50-5f,f0-f7) one after the other through the real ring (388(A5), write index 26(A5)), each preceded by a stop
-- command $f0 and 40 quiet frames, then SW_WAIT frames (default 150) of observation. The Z80 taps (ym writes, oki writes, latch reads) and the 68000 latch writes go to SW_OUT with S markers.
-- This is a poke harness (task slots freed): it measures the Z80 side only.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local fh = assert(io.open(os.getenv("SW_OUT"), "w"))
local START = tonumber(os.getenv("SW_START") or "300")
local WAIT = tonumber(os.getenv("SW_WAIT") or "150")
local ids = {}
for tok in string.gmatch(os.getenv("SW_IDS") or "", "(%x+)") do ids[#ids + 1] = tonumber(tok, 16) end
if #ids == 0 then for i = 0, 0x3f do ids[#ids + 1] = i end; for i = 0x50, 0x5f do ids[#ids + 1] = i end; for i = 0xf0, 0xf7 do ids[#ids + 1] = i end end
local zcpu = manager.machine.devices[":audiocpu"]
local zspace = zcpu.spaces["program"]
local zpc = zcpu.state["CURPC"]
taps = {}
local cur = -1
taps[#taps + 1] = zspace:install_write_tap(0xf000, 0xf001, "ym", function(off, data, mask) fh:write(string.format("f=%d Z ym a=%04x d=%02x pc=%04x\n", L.frame(), off, data & 0xff, zpc.value)) end)
taps[#taps + 1] = zspace:install_write_tap(0xf002, 0xf007, "oki", function(off, data, mask) fh:write(string.format("f=%d Z w a=%04x d=%02x pc=%04x\n", L.frame(), off, data & 0xff, zpc.value)) end)
taps[#taps + 1] = m:install_write_tap(0x800180, 0x800189, "lat68", function(off, data, mask) if (data & 0xff) ~= 0xff then fh:write(string.format("f=%d M w a=%06x d=%04x\n", L.frame(), off, data)) end end)
local A5 = 0xff8000
local function inject(id)
  local wi = m:read_u16(A5 + 26)
  m:write_u16(A5 + 388 + wi, id)
  m:write_u16(A5 + 26, (wi + 2) & 0x7f)
end
local idx, nextf, phase = 1, nil, 0
emu.register_frame_done(function()
  local f = L.frame()
  if f == START then
    for i = 0, 15 do if i ~= 11 then m:write_u8(0xff1000 + 16 * i, 0) end end
    fh:write(string.format("f=%d S freed\n", f))
    nextf = f + 60
  end
  if nextf and f >= nextf and idx <= #ids then
    if phase == 0 then inject(0xf0); phase = 1; nextf = f + 40
    else
      local id = ids[idx]
      fh:write(string.format("f=%d S id=%02x\n", f, id)); inject(id); idx = idx + 1; phase = 0; nextf = f + WAIT
    end
  end
  if idx > #ids and f >= nextf then fh:write(string.format("f=%d S done\n", f)); fh:close(); manager.machine:exit() end
end)
