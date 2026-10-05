-- framecap.lua: oracle for ffframes.build. Calls the game's own object-list builder `$16910` (A0 = a fake record,
-- A6 = output buffer, A5 = $ff8000) once per test line and writes the entries it produced.
-- Run: FF_MAMEARGS="-debug -debugger none" FC_IN=tests.txt FC_OUT=out.txt ffrun.sh framecap.lua 600
-- Input line:  block mirror pal xoff x y camx camy   (hex block; decimal others; x, y, cam* as written into the record/vars)
-- Output line: <test index> <n entries> then x y code attr for each, hex words.
-- Like lua/callcap.lua: the CPU is parked at the VBL entry $53e (registers can only be set there), then each call is
-- PC=$16910, SR=$2700, a sentinel return address; the game never resumes, nothing it would do next matters.
local cpu = manager.machine.devices[":maincpu"]
local mem = cpu.spaces["program"]
local dbg = manager.machine.debugger
assert(dbg, "run with FF_MAMEARGS=\"-debug -debugger none\"")
local tests = {}
for line in io.lines(assert(os.getenv("FC_IN"))) do
  local t = {}
  for tok in line:gmatch("%S+") do t[#t + 1] = tok end
  if #t >= 8 then tests[#tests + 1] = t end
end
local out = assert(io.open(assert(os.getenv("FC_OUT")), "w"))
local SENTINEL = 0x0fff00
local R, OUTBUF, A5 = 0xffe800, 0xffec00, 0xff8000
local frames, armed, cur, started, finished = 0, false, 0, false, false
local function s16(v) return v & 0xffff end

local function setup(t)
  local block, mirror, pal, xoff, x, y, camx, camy = tonumber(t[1], 16), tonumber(t[2]), tonumber(t[3]), tonumber(t[4]),
    tonumber(t[5]), tonumber(t[6]), tonumber(t[7]), tonumber(t[8])
  for i = 0, 0xbf do mem:write_u8(R + i, 0) end
  mem:write_u8(R + 1, 1)
  mem:write_u16(R + 6, s16(x)); mem:write_u16(R + 10, s16(y))
  mem:write_u32(R + 36, block)
  mem:write_u8(R + 46, mirror); mem:write_u8(R + 47, pal); mem:write_u16(R + 48, s16(xoff))
  mem:write_u16(A5 - 28028, s16(camx - 0x40)); mem:write_u16(A5 - 28026, s16(camx - 0x30))
  mem:write_u16(A5 + 1046, s16(camy)); mem:write_u16(A5 + 1042, s16(camx))
  mem:write_u16(A5 + 144, 0x100); mem:write_u16(A5 + 146, 0x100)
  for i = 0, 0x3ff do mem:write_u8(OUTBUF + i, 0) end
  cpu.state["A5"].value = A5
  cpu.state["A0"].value = R
  cpu.state["A6"].value = OUTBUF
  cpu.state["D7"].value = 0
  local sp = 0xff0f00
  mem:write_u32(sp, SENTINEL)
  cpu.state["SP"].value = sp
  cpu.state["SR"].value = 0x2700
  cpu.state["PC"].value = 0x16910
end

emu.register_periodic(function()
  if finished then return end
  frames = frames + 1
  if not started then
    started = true
    dbg:command("bpset 53e")
    dbg:command("go")
    return
  end
  if dbg.execution_state ~= "stop" then return end
  local pc = cpu.state["CURPC"].value
  if not armed then
    if pc == 0x53e and frames > 90 then
      armed = true
      dbg:command("bpclear")
      dbg:command("bpset " .. string.format("%x", SENTINEL))
      cur = 1
      setup(tests[cur])
      dbg:command("go")
    elseif pc == 0x53e then
      dbg:command("go")
    end
    return
  end
  if pc == SENTINEL then
    local a6 = cpu.state["A6"].value
    local n = (a6 - OUTBUF) // 8
    local parts = { string.format("%d %d", cur, n) }
    for i = 0, n - 1 do
      parts[#parts + 1] = string.format("%04x %04x %04x %04x", mem:read_u16(OUTBUF + 8 * i), mem:read_u16(OUTBUF + 8 * i + 2),
        mem:read_u16(OUTBUF + 8 * i + 4), mem:read_u16(OUTBUF + 8 * i + 6))
    end
    out:write(table.concat(parts, " "), "\n")
    cur = cur + 1
    if cur > #tests then finished = true; out:close(); manager.machine:exit(); return end
    setup(tests[cur])
    dbg:command("go")
  end
end)
