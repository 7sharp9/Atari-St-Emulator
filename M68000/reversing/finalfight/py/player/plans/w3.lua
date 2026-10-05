local t = {}
local function hold(f, fl, n) t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end
hold(40, "b1", 4)                  -- break the prop
hold(100, "right", 14)             -- step onto the drop
hold(130, "b1", 4)                 -- pick up
return t
