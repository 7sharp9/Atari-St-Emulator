local t = {}
local function hold(f, fls, n) for _, fl in ipairs(fls) do t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end end
hold(30, {"b1","b2"}, 4)     -- special at hp 3 (hit lands: cost floors at 0)
hold(160, {"b1","b2"}, 4)    -- special again at hp 0
return t
