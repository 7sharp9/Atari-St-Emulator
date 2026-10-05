-- A5 = $ffff8000 (sign-extended): mask register addresses to 24 bits before using them in b@/w@/d@
return {
 {"be9e", "be9e entry a6=%04x ch=%02x in130=%02x in131=%02x face=%02x c162=%04x c160=%02x", "a6&ffff,b@((a6&ffffff)+20),b@((a6&ffffff)+130),b@((a6&ffffff)+131),b@((a6&ffffff)+46),w@((a6&ffffff)+162),b@((a6&ffffff)+160)"},
 {"bf0e", "bf0e scan start", ""},
 {"bf24", "bf24 cand a0=%04x b0=%02x l120=%08x hp=%04x gy=%04x y=%04x b66=%02x", "a0&ffff,b@(a0&ffffff),d@((a0&ffffff)+120),w@((a0&ffffff)+24),w@((a0&ffffff)+14),w@((a0&ffffff)+10),b@((a0&ffffff)+66)"},
 {"bec8", "bec8 FOUND", ""},
 {"bec0", "bec0 no grab", ""},
}
