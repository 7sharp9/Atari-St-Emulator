-- j1: jump attacks. each block: 60 frames idle, action
local t = {}
local function hold(f, fl, n) t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end
-- vertical jump + attack at apex
hold(20, "b2", 4); hold(60, "b1", 4)
-- jump right (hold right through takeoff 12 frames), attack
hold(150, "right", 40); hold(150, "b2", 4); hold(185, "b1", 4)
-- jump + down + attack
hold(300, "b2", 4); hold(325, "down", 25); hold(335, "b1", 4)
-- jump left + attack (away from facing)
hold(450, "left", 40); hold(450, "b2", 4); hold(485, "b1", 4)
return t
