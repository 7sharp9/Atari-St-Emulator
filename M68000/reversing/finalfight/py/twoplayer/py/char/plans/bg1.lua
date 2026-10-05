local t = {}
local function hold(f, fls, n) for _, fl in ipairs(fls) do t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end end
-- four-hit chain at 14-frame spacing, Dug adjacent (+24): after the 3rd hit the 4th press is made with LEFT held (away from facing)
hold(10, {"b1"}, 4); hold(24, {"b1"}, 4); hold(38, {"b1"}, 4)
hold(52, {"left","b1"}, 5)
return t
