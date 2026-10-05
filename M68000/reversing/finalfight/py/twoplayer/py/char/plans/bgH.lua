local t = {}
local function hold(f, fls, n) for _, fl in ipairs(fls) do t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end end
hold(10, {"b1"}, 4); hold(40, {"b1"}, 4)
hold(70, {"left","b1"}, 5)
return t
