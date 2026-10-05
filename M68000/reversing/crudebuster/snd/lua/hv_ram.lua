-- hv_ram.lua: latch values >= $80 set sound-CPU zero-page variables; read them back from the sound RAM ($1f0000 + zp) 3 frames after each write.
--   $27 tempo offset  $28 YM2151 master volume  $29 YM2203 master volume  $2a OKI2 volume  $2b OKI1 volume  ($06/$07 tempo, $08/$09 tempo base)
local SND = os.getenv("SND_DIR")
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local S = dofile(SND .. "/lua/snd_lib.lua")
S.install()
S.mute_demo()
manager.machine.video.throttled = false
local list = {}
for v in (os.getenv("VALS") or "80 9f a0 bf c0 c7 c8 cf d0 df e0 ff"):gmatch("%x+") do list[#list + 1] = tonumber(v, 16) end
local out = assert(io.open(os.getenv("LOG"), "w"))
local i, f0 = 0, nil
local function zp(a) return S.asp:read_u8(0x1f0000 + a) end
emu.register_frame_done(function()
  local f = L.frame()
  if f < 150 then return end
  if f0 == nil then f0 = f end
  local k = (f - f0)
  if k % 6 == 0 then
    i = i + 1
    if i > #list then out:close(); manager.machine:exit(); return end
    L.mem:write_u16(0xbc002, list[i])
  elseif k % 6 == 4 then
    out:write(string.format("cmd %02x  $27=%02x $28=%02x $29=%02x $2a=%02x $2b=%02x  $06/07=%02x%02x $08/09=%02x%02x\n", list[i], zp(0x27), zp(0x28), zp(0x29), zp(0x2a), zp(0x2b), zp(0x07), zp(0x06), zp(0x09), zp(0x08)))
  end
end)
