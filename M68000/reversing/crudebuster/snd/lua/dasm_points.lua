-- dasm_points.lua: MAME disassembly of single instructions at given (bank, logical address) points listed in $CB_OUT/offchain.txt (bank mapped at $e000 via MPR7).
-- result: $CB_OUT/offchain_result.txt  "bank<TAB>addr<TAB>MAME text line"
local out = os.getenv("CB_OUT")
local m = manager.machine
local cpu = m.devices[":audiocpu"]
local d = m.debugger
local res = io.open(out .. "/offchain_result.txt", "w")
local n = 0
for l in io.lines(out .. "/offchain.txt") do
  local b, a = l:match("(%d+) (%x+)")
  cpu.state["MPR7"].value = tonumber(b)
  n = n + 1
  local fn = string.format("%s/oc_%d.txt", out, n)
  d:command(string.format("dasm %s,%s,1,1,:audiocpu", fn, a))
  local f = io.open(fn)
  local line = f:read("*l"); f:close()
  res:write(string.format("%s\t%s\t%s\n", b, a, line))
end
res:close()
cpu.state["MPR7"].value = 0
m:exit()
