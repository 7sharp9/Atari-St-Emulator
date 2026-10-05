local t = {}
local function hold(f, fl, n) t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end
hold(30,"right",30); hold(60,"b2",4); hold(74,"b1",4)
return t
