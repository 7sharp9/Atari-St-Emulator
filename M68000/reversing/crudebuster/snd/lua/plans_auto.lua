-- plans_auto.lua: deterministic pseudo-random autoplay plan generator for a 1P game from coin at 600 to frame N (SEED, N via env).
-- walks right, mashes attack/jump/special, ups/downs; reinserts a coin and starts again when asked (every 3000 frames).
local N = tonumber(os.getenv("AUTO_N") or "8000")
local seed = tonumber(os.getenv("AUTO_SEED") or "12345")
local function rnd() seed = (seed * 1103515245 + 12345) % 2147483648; return (seed >> 8) end
local t = { { 600, "coin", 1 }, { 612, "coin", 0 }, { 700, "start1", 1 }, { 712, "start1", 0 } }
local f = 1000
local hold = {}
local btn = { "b1", "b2", "b3" }
while f < N do
  local r = rnd() % 100
  if r < 55 then t[#t + 1] = { f, "right", 1 }; t[#t + 1] = { f + 60 + rnd() % 120, "right", 0 }
  elseif r < 65 then t[#t + 1] = { f, "up", 1 }; t[#t + 1] = { f + 20 + rnd() % 40, "up", 0 }
  elseif r < 75 then t[#t + 1] = { f, "down", 1 }; t[#t + 1] = { f + 20 + rnd() % 40, "down", 0 }
  elseif r < 82 then t[#t + 1] = { f, "left", 1 }; t[#t + 1] = { f + 10 + rnd() % 30, "left", 0 }
  else
    local b = btn[1 + rnd() % 3]
    t[#t + 1] = { f, b, 1 }; t[#t + 1] = { f + 6, b, 0 }
  end
  f = f + 8 + rnd() % 24
  if f % 3000 < 30 then t[#t + 1] = { f, "coin", 1 }; t[#t + 1] = { f + 12, "coin", 0 }; t[#t + 1] = { f + 100, "start1", 1 }; t[#t + 1] = { f + 112, "start1", 0 } end
end
return t
