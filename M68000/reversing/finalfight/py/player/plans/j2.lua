local t = {}
local function hold(f, fl, n) t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end
hold(20, "b2", 4); hold(36, "b1", 4)                          -- vertical jump, attack mid-air
hold(150, "b2", 4); hold(160, "b1", 4)                        -- attack right after takeoff (still crouch)
hold(260, "b2", 4); hold(290, "b1", 4)                        -- attack late
hold(400, "up", 40); hold(400, "b2", 4); hold(436, "b1", 4)  -- jump up-direction + attack
return t
