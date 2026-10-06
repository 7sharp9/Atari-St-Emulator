-- boot st_uk diskless to the desktop: log per-frame state, detect first non-blank screen, dump DUMPAFTER frames later and exit
local machine = manager.machine
local cpu = machine.devices[":m68000"]
local mem = cpu.spaces["program"]
local screen = machine.screens[":screen"]
local OUT = os.getenv("MAMEST_OUT") or "."
local LAST = tonumber(os.getenv("MAMEST_LAST") or "20000")
local AFTER = tonumber(os.getenv("MAMEST_AFTER") or "300")
local function rd32(a) return (mem:read_u16(a) << 16) | mem:read_u16(a + 2) end
local logf = assert(io.open(OUT .. "/frames.log", "w"))
local t0 = os.clock()
local first, prevh
local function hash(s) local h = 5381 for i = 1, #s do h = (h * 33 + s:byte(i)) & 0xffffffff end return h end
local function dump(f, base)
  local function w(name, data) local o = assert(io.open(string.format("%s/%s_f%d.bin", OUT, name, f), "wb")); o:write(data); o:close() end
  w("low", mem:read_range(0, 0x7ff, 8))
  w("screen", mem:read_range(base, base + 31999, 8))
  local pal = {}
  for i = 0, 15 do pal[#pal+1] = string.char(mem:read_u16(0xff8240 + 2*i) >> 8, mem:read_u16(0xff8240 + 2*i) & 0xff) end
  w("pal", table.concat(pal))
  w("ram", mem:read_range(0, 0xfffff, 8))
  logf:write(string.format("DUMP f=%d rez=%02x shifter_base=%02x%02x%02x\n", f, mem:read_u8(0xff8260), mem:read_u8(0xff8201), mem:read_u8(0xff8203), mem:read_u8(0xff820d)))
  pcall(function() screen:snapshot(string.format("%s/snap_f%d.png", OUT, f)) end)
end
emu.register_frame_done(function()
  local f = screen:frame_number()
  local base = rd32(0x44e)
  local h = 0
  if base >= 0x1000 and base < 0x100000 then h = hash(mem:read_range(base, base + 31999, 8)) end
  if f % 10 == 0 or h ~= prevh then
    logf:write(string.format("%d base=%06x frclock=%d hz200=%d scrhash=%08x pc=%06x t=%.2f\n", f, base, rd32(0x466), rd32(0x4ba), h, cpu.state["PC"].value, os.clock() - t0))
  end
  prevh = h
  if not first and h ~= 0 and h ~= 0x550c3505 and f > 100 then first = f logf:write("FIRST_NONBLANK " .. f .. "\n") end
  if first and f == first + AFTER then dump(f, base) logf:close() machine:exit() end
  if f >= LAST then logf:close() machine:exit() end
end)
