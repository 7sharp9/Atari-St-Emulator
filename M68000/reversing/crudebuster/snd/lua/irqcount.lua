-- irqcount.lua: HuC6280 entry-point counters through debugger breakpoints (run with `cbmame.sh script`, i.e. -debug -debugger none).
--   Each breakpoint's action increments a debugger temp variable and continues; the totals are printed at CB_STOP.
--   env: SND_DIR, CB_DIR, CB_PLAN (input plan like drive.lua), CB_STOP, LOG, CMDS ("frame:hex,..." latch writes from Lua), MUTE=1
--   points (logical HuC6280 addresses, taken from rd.txt):  e16d IRQ2 vector (YM2151 timer B), e0e4 timer vector, e200 IRQ1 vector (latch),
--   e134 alt IRQ2 path ($63 != 0), e5be channel engine tick, e302 FIFO pop, e65a tempo accumulator, f855 second engine, fd9c clock, ...
local SND = os.getenv("SND_DIR")
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local m = manager.machine
m.video.throttled = false
local aud = m.devices[":audiocpu"]
local pts = {}
for a in (os.getenv("PTS") or "e16d e0e4 e200 e134 e5be e302 e65a f855 fd9c fc71 f651 f726 e7ee e6a5 e925 e248"):gmatch("%x+") do pts[#pts + 1] = a end
m.debugger:command("focus :audiocpu")
for i, a in ipairs(pts) do
  aud.debug:bpset(tonumber(a, 16), "", string.format("temp%d = temp%d + 1; g", i - 1, i - 1))
end
if os.getenv("MUTE") == "1" then
  m.ioport.ports[":DSW"].fields["Demo Sounds"]:set_value(0x8000)
end
local sched = {}
if os.getenv("CB_PLAN") then sched = dofile(os.getenv("CB_PLAN")) end
local cmds = {}
for f, v in (os.getenv("CMDS") or ""):gmatch("(%d+):(%x+)") do cmds[#cmds + 1] = { tonumber(f), tonumber(v, 16) } end
local stop = tonumber(os.getenv("CB_STOP") or "1000")
local nlat = 0
local lat = {}
TAPLAT = L.mem:install_write_tap(0xbc002, 0xbc003, "lat", function(off, data, mask) nlat = nlat + 1 end)
emu.register_frame_done(function()
  local f = L.frame()
  for _, e in ipairs(sched) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  for _, c in ipairs(cmds) do if c[1] == f then L.mem:write_u16(0xbc002, c[2]) end end
  if f >= stop then
    for i = 1, #pts do m.debugger:command(string.format("printf \"CNT%d %%d\\n\", temp%d", i - 1, i - 1)) end
    local cl = m.debugger.consolelog
    local vals = {}
    for i = 1, #cl do
      local k, v = cl[i]:match("^CNT(%d+) (%-?%d+)")
      if k then vals[tonumber(k) + 1] = v end
    end
    local o = assert(io.open(os.getenv("LOG"), "w"))
    o:write("frames " .. f .. "\nlatch_writes_68k " .. nlat .. "\n")
    for i, a in ipairs(pts) do o:write(string.format("%s %s\n", a, vals[i] or "?")) end
    o:close()
    m:exit()
  end
end)
