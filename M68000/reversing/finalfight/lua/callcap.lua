-- callcap for MAME: call a 68000 routine in a warmed-up machine and report what it changed.
--
-- Usage (from M68000/reversing/finalfight/):
--   CALLCAP_SPEC=lua/specs/foo.lua ./ffmame.sh callcap
--
-- The spec file returns a table:
--   addr   routine entry (required)
--   warm   frames to run before the call (default 600)
--   regs   { D0=0x53, A0=0x908500, ... }  hex-valued presets (like the ST callcap)
--   pokes  { {addr, value, width}, ... }  width 1|2|4, default 1; applied after the warm-up
--   ranges { {base, len}, ... }           memory diffed (default work RAM + gfx RAM)
--   max    frame budget for the call before giving up (default 600)
--   cpu    device tag (default ":maincpu")
--
-- The call runs with SR=$2700 (interrupts masked) like the ST callcap, with a sentinel return
-- address pushed at A7. Output lines are prefixed `callcap:` so a driver script can grep them:
--   regdelta <reg> <old> <new>      only registers that changed
--   mem <addr> <n> <old bytes> -> <new bytes>    one line per contiguous changed run
--   result returned | no_return pc=<..>

local spec_path = os.getenv("CALLCAP_SPEC")
assert(spec_path, "set CALLCAP_SPEC to a spec file")
local spec = dofile(spec_path)

local SENTINEL = 0x0fff00 -- inside the program ROM map, never fetched by the game
local cpu = manager.machine.devices[spec.cpu or ":maincpu"]
local mem = cpu.spaces["program"]
local dbg = manager.machine.debugger
assert(dbg, "run MAME with -debug -debugger none")

local ranges = spec.ranges or { { 0xff0000, 0x10000 }, { 0x900000, 0x30000 } }
local warm = spec.warm or 600
local budget = spec.max or 600
local REGS = { "D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7",
               "A0", "A1", "A2", "A3", "A4", "A5", "A6", "SP", "SR" }

local function say(fmt, ...) print("callcap: " .. string.format(fmt, ...)) end

local function snapshot()
  local s = {}
  for _, r in ipairs(ranges) do
    local base, len = r[1], r[2]
    local t = {}
    for i = 0, len - 1 do t[i] = mem:read_u8(base + i) end
    s[#s + 1] = { base = base, len = len, bytes = t }
  end
  return s
end

local function getregs()
  local t = {}
  for _, r in ipairs(REGS) do t[r] = cpu.state[r].value end
  return t
end

local pre_regs, pre_mem
local frames, called_at, armed = 0, nil, false
local at = spec.at or 0x53e -- VBL entry: a frame-synchronous point where the CPU is stopped

-- -debug starts the machine stopped. Break at the VBL entry once per frame; after `warm` of them
-- the CPU is stopped between instructions, which is the only point where setting registers is
-- reliable (setting PC from a free-running timeslice did not take, checked: PC stayed in the
-- idle loop and the sentinel was never reached).
emu.register_periodic(function()
  if frames == 0 then
    dbg:command(string.format("bpset %x", at))
    dbg:command("go")
  end
  frames = frames + 1
  if armed or dbg.execution_state ~= "stop" or cpu.state["CURPC"].value ~= at then return end
  if frames < warm then
    dbg:command("go")
    return
  end
  armed = true
  dbg:command("bpclear")
  pre_regs = getregs()
  for k, v in pairs(spec.regs or {}) do cpu.state[k].value = v end
  for _, p in ipairs(spec.pokes or {}) do
    local a, v, w = p[1], p[2], p[3] or 1
    if w == 1 then mem:write_u8(a, v) elseif w == 2 then mem:write_u16(a, v) else mem:write_u32(a, v) end
  end
  local sp = cpu.state["SP"].value - 4
  mem:write_u32(sp, SENTINEL)
  cpu.state["SP"].value = sp
  cpu.state["SR"].value = 0x2700
  pre_mem = snapshot() -- after pokes and the sentinel push: the diff is the routine's own effect
  cpu.state["PC"].value = spec.addr
  called_at = frames
  dbg:command(string.format("bpset %x", SENTINEL))
  dbg:command("go")
end)

local done = false
emu.register_periodic(function()
  if done or not called_at then return end
  local pc = cpu.state["CURPC"].value
  if dbg.execution_state == "stop" and pc == SENTINEL then
    done = true
    local post = getregs()
    -- a clean rts pops the sentinel, so A7 is back at its entry value
    for _, r in ipairs(REGS) do
      local want = (spec.regs and spec.regs[r]) or pre_regs[r]
      if r == "SR" then want = 0x2700 end
      if r == "SP" then want = pre_regs["SP"] end
      if post[r] ~= want then say("regdelta %s %08x %08x", r, want, post[r]) end
    end
    for _, s in ipairs(pre_mem) do
      local i = 0
      while i < s.len do
        if mem:read_u8(s.base + i) ~= s.bytes[i] then
          local j = i
          while j < s.len and mem:read_u8(s.base + j) ~= s.bytes[j] do j = j + 1 end
          local o, n = {}, {}
          for k = i, math.min(j - 1, i + 15) do
            o[#o + 1] = string.format("%02x", s.bytes[k])
            n[#n + 1] = string.format("%02x", mem:read_u8(s.base + k))
          end
          say("mem %06x %d %s -> %s", s.base + i, j - i, table.concat(o, " "), table.concat(n, " "))
          i = j
        else
          i = i + 1
        end
      end
    end
    say("result returned")
    manager.machine:exit()
  elseif frames - called_at > budget then
    done = true
    say("result no_return pc=%06x state=%s", pc, dbg.execution_state)
    manager.machine:exit()
  end
end)
