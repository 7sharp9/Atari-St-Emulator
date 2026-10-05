local t = {}
local function hold(f, fl, n) t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end
hold(40, "b1", 4)          -- break the prop (kill on frame ~44..45)
hold(44, "right", 2)       -- direction press near the kill frame
return t
