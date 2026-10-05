local t = {}
local function hold(f, fls, n) for _, fl in ipairs(fls) do t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end end
hold(20, {"right"}, 60); hold(120, {"left"}, 60); hold(220, {"up"}, 60); hold(320, {"down"}, 60)
hold(420, {"right","up"}, 60); hold(520, {"left","down"}, 60)
return t
