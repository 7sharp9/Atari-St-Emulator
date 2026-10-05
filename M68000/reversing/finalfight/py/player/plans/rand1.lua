-- deterministic pseudo-random input plan: every 6..30 frames re-roll direction (hold) and pulse buttons
local seed = tonumber(os.getenv("FF_SEED") or "12345")
local function rnd(n) seed = (seed * 1103515245 + 12345) & 0x7fffffff; return (seed >> 16) % n end
local t = {}
local f = 5
local N = tonumber(os.getenv("FF_N") or "3000")
local dirs = {"right","left","up","down"}
local held = {}
while f < N do
  -- directions
  for _, d in ipairs(dirs) do t[#t+1] = {f, d, 0} end
  local r = rnd(10)
  if r < 4 then t[#t+1] = {f, "right", 1} elseif r < 8 then t[#t+1] = {f, "left", 1} end
  local v = rnd(10)
  if v < 3 then t[#t+1] = {f, "up", 1} elseif v < 5 then t[#t+1] = {f, "down", 1} end
  -- buttons
  local b = rnd(10)
  if b < 4 then t[#t+1] = {f, "b1", 1}; t[#t+1] = {f + 4, "b1", 0}
  elseif b < 6 then t[#t+1] = {f, "b2", 1}; t[#t+1] = {f + 4, "b2", 0}
  elseif b == 6 then t[#t+1] = {f, "b1", 1}; t[#t+1] = {f, "b2", 1}; t[#t+1] = {f + 4, "b1", 0}; t[#t+1] = {f + 4, "b2", 0} end
  f = f + 6 + rnd(25)
end
return t
