local t = {}
local function hold(f, fl, n) t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end
hold(20, "left", 30); hold(20, "b2", 4); hold(36, "down", 8); hold(36, "b1", 4)
return t
