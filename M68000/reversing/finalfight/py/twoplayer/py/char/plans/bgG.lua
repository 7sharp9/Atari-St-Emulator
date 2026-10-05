local t = {}
local function hold(f, fls, n) for _, fl in ipairs(fls) do t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end end
hold(10, {"b1"}, 4); hold(24, {"b1"}, 4); hold(38, {"b1"}, 4); hold(52, {"b1"}, 4)
hold(66, {"left","b1"}, 5)
return t
