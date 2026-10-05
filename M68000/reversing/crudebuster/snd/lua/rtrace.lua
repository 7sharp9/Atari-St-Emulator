-- rtrace.lua: ordered trace of the HuC6280 sequencer using a read tap on the sound ROM (no debugger needed).
--   Every data read of the ROM ($000000-$00ffff) whose HuC6280 PC (after the reading instruction) is one of the sequencer's read sites is logged:
--     F ch ptr y byte      event parser $E6A7 `lda ($0B),y`   (ch = zero page $1F, ptr = $0B/$0C, y = Y register before the read)
--     G ch ptr y byte      loop $E952 `lda ($0B),y`
--     D ch idx             opcode table read $E96B `lda $E97A,x`  (idx = (offset-$97a)/2)
--     O id oki             OKI table read in $F651 (id = table index; oki = $53)
--   plus the chip writes and latch events of snd_lib (E lines) so that stream bytes and chip writes appear in execution order.
--   env: SND_DIR LOG CMDS ("frame:hex,...") CB_STOP MUTE(default 1)
local SND = os.getenv("SND_DIR")
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local S = dofile(SND .. "/lua/snd_lib.lua")
S.install({ keep14 = false })
local m = manager.machine
m.video.throttled = false
if os.getenv("MUTE") ~= "0" then S.mute_demo() end
local aud, asp = S.aud, S.asp
local st = aud.state
local trace = {}
local function ram(a) return asp:read_u8(0x1f0000 + a) end
local function frame() return S.screen:frame_number() end
local TB = { [0x7e56] = true }
local oki_base = { 0x7e56, 0x7f12, 0x8012 }
S.hold[#S.hold + 1] = asp:install_read_tap(0x0, 0xffff, "rom_rd", function(off, data, mask)
  local pc = st["PC"].value
  if (pc == 0xe6a9 or pc == 0xe954) and off >= 0x2000 then
    local ptr = ram(0x0b) | ram(0x0c) << 8
    trace[#trace + 1] = string.format("%s %d %04x %d %02x", pc == 0xe6a9 and "F" or "G", ram(0x1f), ptr, st["Y"].value, data & 0xff)
  elseif pc == 0xe96e and off >= 0x97a and off < 0xa0a then
    trace[#trace + 1] = string.format("D %d %d", ram(0x1f), (off - 0x97a) // 2)
  elseif pc == 0xf68b and off >= 0x7000 then
    -- `lda ($54),y` y = idx*4+3 : byte 3 of a 4-byte OKI table entry
    local base = ram(0x54) | ram(0x55) << 8
    trace[#trace + 1] = string.format("O %d %d %d", (off - 3) // 4, ram(0x53), off)
  end
end)
local cmds = {}
for f, v in (os.getenv("CMDS") or ""):gmatch("(%d+):(%x+)") do cmds[#cmds + 1] = { tonumber(f), tonumber(v, 16) } end
local stop = tonumber(os.getenv("CB_STOP") or "600")
local log = assert(io.open(os.getenv("LOG"), "w"))
local nev, nlat, ntr = 0, 0, 0
-- merge: chip events were appended to S.ev, stream events to trace; keep relative order by flushing both at every frame is not enough,
-- so chip events are also pushed into `trace` through a wrapper: poll S.ev length inside the read tap.
local lastn = 0
local function sync()
  for i = lastn + 1, #S.ev do
    local e = S.ev[i]
    trace[#trace + 1] = string.format("E %s %s %02x", e[2], e[3], e[4])
  end
  lastn = #S.ev
end
-- wrap the tap: call sync before logging by redefining S.ev append through metatable
setmetatable(S.ev, { __newindex = function(t, k, v)
  rawset(t, k, v)
  trace[#trace + 1] = string.format("E %s %s %02x", v[2], v[3], v[4])
end })
emu.register_frame_done(function()
  local f = frame()
  trace[#trace + 1] = "FR " .. f .. " " .. tostring(S.tick[f] or 0)
  for _, c in ipairs(cmds) do if c[1] == f then L.mem:write_u16(0xbc002, c[2]); trace[#trace + 1] = string.format("SEND %02x", c[2]) end end
  for i = 1, #trace do log:write(trace[i], "\n") end
  trace = {}
  if f >= stop then log:close(); m:exit() end
end)
