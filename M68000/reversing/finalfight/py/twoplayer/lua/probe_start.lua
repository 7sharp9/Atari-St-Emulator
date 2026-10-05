-- probe_start.lua: cold boot, schedule from FFD_SCHED (a lua file returning {{frame, field, level},...}), log game flow every FFD_EVERY frames.
-- FFD_STOP frame to exit; FFD_SHOTS=f1,f2,.. screenshots (named by frame); FFD_LOG log path.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local out = os.getenv("FF_OUT")
local sched = dofile(os.getenv("FFD_SCHED"))
local stop = tonumber(os.getenv("FFD_STOP") or "1800")
local every = tonumber(os.getenv("FFD_EVERY") or "10")
local lo = tonumber(os.getenv("FFD_LO") or "1000")
local log = io.open(os.getenv("FFD_LOG") or (out .. "/probe.log"), "w")
local shots = {}
for n in string.gmatch(os.getenv("FFD_SHOTS") or "", "%d+") do shots[tonumber(n)] = true end
local A5 = 0xff8000
local dumps = {}
for n in string.gmatch(os.getenv("FFD_DUMP") or "", "%d+") do dumps[tonumber(n)] = true end
-- write/read taps: FF_W="a-b,c-d" FF_R=... output FF_TAP_OUT, frames FF_TAP_LO..HI
local tlo = tonumber(os.getenv("FF_TAP_LO") or "0")
local thi = tonumber(os.getenv("FF_TAP_HI") or "99999")
local fh = io.open(os.getenv("FF_TAP_OUT") or (out .. "/tap.txt"), "w")
local cpu = manager.machine.devices[":maincpu"]
local pcreg = cpu.state["CURPC"]
local function tlog(kind, offset, data, mask)
  local fr = L.frame()
  if fr < tlo or fr > thi then return end
  fh:write(string.format("f=%d pc=%06x %s a=%06x m=%04x d=%04x\n", fr, pcreg.value, kind, offset, mask, data))
end
taps = {}
for kind, env in pairs({ w = "FF_W", r = "FF_R" }) do
  for a, b in string.gmatch(os.getenv(env) or "", "(%x+)-(%x+)") do
    local fn = function(offset, data, mask) local ok, e = pcall(tlog, kind, offset, data, mask); if not ok then print("TAP ERR " .. tostring(e)) end end
    if kind == "w" then taps[#taps + 1] = L.mem:install_write_tap(tonumber(a, 16), tonumber(b, 16), "w" .. a, fn)
    else taps[#taps + 1] = L.mem:install_read_tap(tonumber(a, 16), tonumber(b, 16), "r" .. a, fn) end
  end
end
emu.register_frame_done(function()
  local f = L.frame()
  L.apply(sched, f)
  if f >= lo and f % every == 0 then
    local function rec(a)
      return string.format("[%02x%02x st=%02x%02x ch=%02x x=%04x y=%04x hp=%04x/%04x lv=%02x]", m:read_u8(a), m:read_u8(a + 1), m:read_u8(a + 2), m:read_u8(a + 3), m:read_u8(a + 20),
        m:read_u16(a + 6), m:read_u16(a + 14), m:read_u16(a + 24), m:read_u16(a + 28), m:read_u8(a + 128)) .. string.format("c129=%02x", m:read_u8(a + 129))
    end
    log:write(string.format("%d ph=%04x m127=%02x cr=%04x s190=%02x%02x in=%04x/%04x P1%s P2%s\n", f, m:read_u16(A5), m:read_u8(A5 + 127), m:read_u16(A5 + 76),
      m:read_u8(A5 + 190), m:read_u8(A5 + 191), m:read_u16(0xff8000 + 92), m:read_u16(A5 + 94), rec(0xff8568), rec(0xff8628)))
    log:flush()
  end
  if dumps[f] then L.write(string.format("%s/ram_%05d.bin", out, f), L.ram()) end
  if shots[f] then L.screen:snapshot(string.format("p4d_%05d.png", f)) end
  if f >= stop then log:close(); fh:close(); manager.machine:exit() end
end)
