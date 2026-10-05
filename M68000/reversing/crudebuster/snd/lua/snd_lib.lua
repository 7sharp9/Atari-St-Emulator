-- snd_lib.lua: taps for the Crude Buster sound system (MAME set cbuster).
--   * 68000 writes to the sound latch $bc002 (byte, with frame number)
--   * HuC6280 writes to the four sound chips: YM2203 $100000/1, YM2151 $110000/1, OKI1 $120000/1, OKI2 $130000/1
--   * HuC6280 reads of the latch $140000
-- Every record carries the frame number and the HuC6280 logical PC (the instruction after the access).
local M = {}
local machine = manager.machine
local main = machine.devices[":maincpu"]
local aud = machine.devices[":audiocpu"]
M.main, M.aud = main, aud
M.mem = main.spaces["program"]
M.asp = aud.spaces["program"]
M.screen = machine.screens[":screen"]
M.ev = {}        -- chip writes: {frame, chip, kind, data, pc}   kind: 'a' address/command, 'd' data, 'w' (oki write)
M.lat = {}       -- latch writes by the 68000: {frame, value}
M.latrd = {}     -- latch reads by the HuC6280: {frame, value, pc}
M.irqs = {}
M.hold = {}
local function pc() return aud.state["PC"].value end
local function frame() return M.screen:frame_number() end

function M.install(opt)
  opt = opt or {}
  local lastreg = {}
  M.tick = {}   -- per frame count of YM2151 reg $14 address writes (one per IRQ2 handler run, plus the init ones)
  local function chip(name, base)
    M.hold[#M.hold + 1] = M.asp:install_write_tap(base, base + 1, "w_" .. name, function(off, data, mask)
      local isaddr = (off & 1) == 0
      data = data & 0xff
      if name == "ym2151" and not opt.keep14 then
        if isaddr then
          lastreg[name] = data
          if data == 0x14 then local f = frame(); M.tick[f] = (M.tick[f] or 0) + 1; return end
        elseif lastreg[name] == 0x14 then return end
      end
      M.ev[#M.ev + 1] = { frame(), name, isaddr and "a" or "d", data, pc() }
    end)
  end
  chip("ym2203", 0x100000); chip("ym2151", 0x110000); chip("oki1", 0x120000); chip("oki2", 0x130000)
  M.hold[#M.hold + 1] = M.mem:install_write_tap(0xbc002, 0xbc003, "w_latch", function(off, data, mask)
    -- caller: the 68000 is inside $e1c (called by `jsr $e1c`): the return address is at the top of the stack
    local sp = main.state["SP"].value
    local ret = M.mem:read_u32(sp)
    M.lat[#M.lat + 1] = { frame(), data & 0xff, ret, main.state["PC"].value }
  end)
  M.hold[#M.hold + 1] = M.asp:install_read_tap(0x140000, 0x140001, "r_latch", function(off, data, mask)
    M.latrd[#M.latrd + 1] = { frame(), data & 0xff, pc() }
  end)
end

function M.reset() M.ev = {}; M.lat = {}; M.latrd = {}; M.tick = {} end

-- mute the 68000's own sound sends in attract: DSW "Demo Sounds" off ($80054 bit 7 clear; $80040 bit 7 is still clear until P1 start)
function M.mute_demo()
  local f = machine.ioport.ports[":DSW"].fields["Demo Sounds"]
  f:set_value(0x8000)
end
return M
