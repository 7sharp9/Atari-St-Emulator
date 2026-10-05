-- poke_hp.lua: controlled experiment on Cody's record after FF_LOAD=ff_gameplay.
--  frame 2205: lives byte +128 ($ff85e8) := 5       -> expect HUD digit tile k=0 at $90880c to read 4
--  frame 2215: health word +24 ($ff8580) := $0040   -> expect P1 bar decode 64
--  frame 2300: health word +24 := 0                 -> Cody dies; log writers of +128 and the state words
-- Output FF_POKE_OUT: one line per frame plus write-tap lines (kind "x") for +128/+129 ($ff85e8) and +0..+3 ($ff8568).
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local out = assert(io.open(os.getenv("FF_POKE_OUT") or "poke.txt", "w"))
local m = L.mem
local cpu = manager.machine.devices[":maincpu"]
local pcreg = cpu.state["CURPC"]
local function tap(lo, hi, tag)
  return m:install_write_tap(lo, hi, tag, function(offset, data, mask)
    out:write(string.format("f=%d x pc=%06x a=%06x m=%04x d=%04x\n", L.frame(), pcreg.value, offset, mask, data))
  end)
end
taps = { tap(0xff85e8, 0xff85e9, "lives"), tap(0xff8568, 0xff856b, "state"), tap(0xff8580, 0xff8583, "hp") }
local function row(base)
  local t = {}
  for k = 0, 19 do t[#t + 1] = string.format("%04x", m:read_u16(base + 128 * k)) end
  return table.concat(t, ",")
end
emu.register_frame_done(function()
  local f = L.frame()
  if f == 2205 then m:write_u8(0xff85e8, 5) end
  if f == 2215 then m:write_u16(0xff8580, 0x40) end
  if f == 2300 then m:write_u16(0xff8580, 0) end
  out:write(string.format("f=%d hp=%04x,%04x lives=%02x%02x s=%02x%02x%02x%02x digits=%04x,%04x,%04x r0=%s\n", f,
    m:read_u16(0xff8580), m:read_u16(0xff8582), m:read_u8(0xff85e8), m:read_u8(0xff85e9),
    m:read_u8(0xff8568), m:read_u8(0xff8569), m:read_u8(0xff856a), m:read_u8(0xff856b),
    m:read_u16(0x90880c), m:read_u16(0x90880c + 128), m:read_u16(0x90880c + 256), row(0x908590)))
  out:flush()
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
