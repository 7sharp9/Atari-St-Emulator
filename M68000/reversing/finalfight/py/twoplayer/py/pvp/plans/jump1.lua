-- P1: vertical jump then attack at frame 40; special at frame 150; jump-kick forward at 260
local t = {}
local function hold(f, fls, n) for _, fl in ipairs(fls) do t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end end
hold(10, {"b2"}, 4); hold(30, {"b1"}, 4)
hold(150, {"b1","b2"}, 4)
hold(260, {"b2"}, 4); hold(262, {"right"}, 40); hold(285, {"b1"}, 4)
return t
