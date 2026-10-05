-- mpr_idle.lua: HuC6280 state samples (once per frame, frames 100-500): the idle loop ($E0E2) and the IRQ2 handler show different MPR5/MPR6/IM/TMR.
-- proves the init layout derived from $E005-$E0E1 (MPR0-7 = ff f8 01 02 03 08 09 00, IM = 4 timer masked) and the handler layout (MPR5/6 = 4/5, IM = 1).
local m = manager.machine
local aud = m.devices[":audiocpu"]
local n = 0
local seen = {}
local o = assert(io.open(os.getenv("LOG"), "w"))
emu.register_frame_done(function()
  n = n + 1
  if n >= 100 then
    local t = {}
    for i = 0, 7 do t[#t + 1] = string.format("%02x", aud.state["MPR" .. i].value) end
    local pc = aud.state["PC"].value
    local cls = (pc == 0xe0e2 or pc == 0xe0e3) and "idle" or (pc >= 0xe000 and "bank0 code" or "other")
    local key = cls .. " MPR0-7 " .. table.concat(t, " ") .. string.format(" IM %02x TMR %02x", aud.state["IM"].value, aud.state["TMR"].value)
    seen[key] = (seen[key] or 0) + 1
  end
  if n == 500 then
    for k, v in pairs(seen) do o:write(string.format("%4d  %s\n", v, k)) end
    o:close(); m:exit()
  end
end)
