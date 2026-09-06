using System.Text.Json;
using Godot;
using PmLogic;
using PmProjection = PmLogic.Projection; // Godot.Projection (4x4 matrix) shadows PmLogic.Projection

namespace PowerMongerPort;

/// <summary>
/// Software-layer terrain renderer: shape (1) of SPEC.md section 8 / README
/// "Next steps" item 1. Every frame (only redrawn when the camera cell moves)
/// it runs the real 68000 pipeline in F# — Projection.projectGrid ($fecc) then
/// Fill.walkQ3 ($fccc quadrant 3 -> $ef62 -> the $e420 DDA + dither fill) —
/// into a 320x200 palette-index buffer, then blits that through the captured
/// shifter palette into an Image/ImageTexture shown on a TextureRect. This is
/// the closest shape to PM's own direct-to-shifter pipeline and is the only
/// shape that keeps the dither pattern.
///
/// Scope: the terrain layer only. All 4 yaw-quadrant grid-walk handlers are
/// now ported (Fill.walk dispatches on yawSteps the same way $f97e/$f982
/// does — see SPEC.md section 4 "the yaw-quadrant grid walk"), so PageUp/
/// PageDown rotate the camera through all 16 yaw steps live.
/// Uncovered pixels (the $78000 master: HUD, stone border, pre-baked sea) are
/// not exported yet (Task 2, SPEC.md section 6/9) so they are left magenta,
/// same "uncovered" convention as assets/reference/render_faithful.png.
/// Arrow keys pan the camera cell to prove the wiring is live, not a single
/// static blit — see README.md "Verification (82nd pass)".
/// </summary>
public partial class TerrainView : Node2D
{
    [Export] public string AssetsDir = "res://assets";
    [Export] public int CamCellX = 36; // $4bb3a - $57ffc, mission-1 start
    [Export] public int CamCellY = 47; // $4bb3c - $57ffc
    [Export] public int YawSteps = 15; // $ff9a >> 4 (0..15); 15 = $f0, quadrant 3, mission-1 start
    [Export] public int PixelScale = 3;

    private static readonly Color Uncovered = new(1f, 0f, 1f); // magenta, matches render_faithful.png
    private static readonly string[] QuadrantNames = { "q0", "q1", "q2", "q3" };

    private Terrain.Map _map = null!;  // set in _Ready, before any other use
    private byte[] _dither = System.Array.Empty<byte>();
    private Color[] _palette = new Color[16];

    // Per-cell entity pass (SPEC.md section 6 / Task 2). entities.json's
    // render_entities[] is one frame's $47970 bucket walk, baked for the
    // mission-1 start pose (cam 36,47 yaw 15) by tools/pm_export.py — byte-exact
    // against tools/pm_render_ref.py load_ram. Only drawn when the live camera
    // matches that pose (the records carry that pose's sub-cell fractions).
    private Sprites.EntityRec[] _entRecs = System.Array.Empty<Sprites.EntityRec>();
    private byte[] _sheet33 = System.Array.Empty<byte>();
    private byte[] _sheetProp = System.Array.Empty<byte>();
    private int _entCamX, _entCamY, _entYaw, _entTileOff, _entRotPhase, _entSelGroup;
    private bool _entAnim;

    private TextureRect _rect = null!; // set in _Ready
    private Label _label = null!;      // set in _Ready
    private int _camX, _camY, _yawSteps;

    // Eye 320, Horizon 130, Zoom 21, Half 4 (zoom index 4) — only YawSteps varies live.
    private PmProjection.Params Proj => PmProjection.Params.Mission1.WithYaw(_yawSteps);

    // grid walk reads cells [camX .. camX+7] x [camY .. camY+7] (Fill.walkQ3) and
    // projects corners [camX .. camX+8] x [camY .. camY+8] (Projection.projectGrid,
    // n = 2*Half+1 = 9) — clamp so both stay inside the 64x128 terrain planes.
    private const int MinCamX = 0, MaxCamX = Terrain.Width - 9;
    private const int MinCamY = 0, MaxCamY = Terrain.Height - 9;

    public override void _Ready()
    {
        var terrainRaw = FileAccess.GetFileAsBytes($"{AssetsDir}/terrain.bin");
        if (terrainRaw.Length == 0)
        {
            GD.PushError($"terrain.bin not found under {AssetsDir}; run tools/pm_export.py");
            return;
        }
        _map = Terrain.parse(terrainRaw);
        _dither = FileAccess.GetFileAsBytes($"{AssetsDir}/dither.bin");
        LoadPalette($"{AssetsDir}/palette.json");
        LoadEntities($"{AssetsDir}/entities.json");

        _camX = Mathf.Clamp(CamCellX, MinCamX, MaxCamX);
        _camY = Mathf.Clamp(CamCellY, MinCamY, MaxCamY);
        _yawSteps = ((YawSteps % 16) + 16) % 16;

        _rect = new TextureRect
        {
            TextureFilter = CanvasItem.TextureFilterEnum.Nearest,
            Scale = new Vector2(PixelScale, PixelScale),
        };
        AddChild(_rect);

        _label = new Label { Position = new Vector2(4, Fill.ScreenHeight * PixelScale + 4) };
        AddChild(_label);

        RenderFrame();
    }

    public override void _UnhandledInput(InputEvent ev)
    {
        if (ev is not InputEventKey { Pressed: true, Echo: false } key) return;
        int dx = key.Keycode switch { Key.Left => -1, Key.Right => 1, _ => 0 };
        int dy = key.Keycode switch { Key.Up => -1, Key.Down => 1, _ => 0 };
        int dyaw = key.Keycode switch { Key.Pageup => 1, Key.Pagedown => -1, _ => 0 };
        if (dx == 0 && dy == 0 && dyaw == 0) return;
        int nx = Mathf.Clamp(_camX + dx, MinCamX, MaxCamX);
        int ny = Mathf.Clamp(_camY + dy, MinCamY, MaxCamY);
        int nyaw = ((_yawSteps + dyaw) % 16 + 16) % 16; // $ff9a's 16-step wrap
        if (nx == _camX && ny == _camY && nyaw == _yawSteps) return;
        _camX = nx;
        _camY = ny;
        _yawSteps = nyaw;
        RenderFrame();
    }

    private void LoadEntities(string path)
    {
        var json = FileAccess.GetFileAsString(path);
        if (string.IsNullOrEmpty(json)) return;
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        if (!root.TryGetProperty("render_entities", out var recs)) return;
        var ctx = root.GetProperty("entity_ctx");
        _entCamX = ctx.GetProperty("cam_x").GetInt32();
        _entCamY = ctx.GetProperty("cam_y").GetInt32();
        _entYaw = ctx.GetProperty("yaw").GetInt32();
        _entAnim = ctx.GetProperty("anim").GetInt32() != 0;
        _entSelGroup = ctx.GetProperty("sel_group").GetInt32();
        _entTileOff = ctx.GetProperty("tile_off").GetInt32();
        _entRotPhase = ctx.GetProperty("rot_phase").GetInt32();
        _sheet33 = FileAccess.GetFileAsBytes($"{AssetsDir}/{ctx.GetProperty("sheet33").GetString()}");
        _sheetProp = FileAccess.GetFileAsBytes($"{AssetsDir}/{ctx.GetProperty("sheet_prop").GetString()}");

        var list = new System.Collections.Generic.List<Sprites.EntityRec>();
        foreach (var o in recs.EnumerateArray())
        {
            int G(string k) => o.GetProperty(k).GetInt32();
            list.Add(new Sprites.EntityRec(
                G("b6"), G("b5"), G("b7"), G("b14"), G("b17"), G("b31"),
                G("fx"), G("fy"), G("fx4"), G("fy4"), G("group"), G("wcx"), G("wcy")));
        }
        _entRecs = list.ToArray();
        GD.Print($"loaded {_entRecs.Length} render entities (pose cam {_entCamX},{_entCamY} yaw {_entYaw})");
    }

    private void LoadPalette(string path)
    {
        using var doc = JsonDocument.Parse(FileAccess.GetFileAsString(path));
        var rgb = doc.RootElement.GetProperty("palettes")[0].GetProperty("rgb");
        for (int i = 0; i < 16; i++)
        {
            var c = rgb[i];
            _palette[i] = Color.Color8(
                (byte)c[0].GetInt32(), (byte)c[1].GetInt32(), (byte)c[2].GetInt32());
        }
    }

    private void RenderFrame()
    {
        var proj = Proj;
        var corners = PmProjection.projectGrid(proj, _map, _camX, _camY);
        var buf = Fill.Buffer.Create();
        Fill.walk(buf, _dither, corners, _map, _camX, _camY, 0, _yawSteps);

        // Per-cell entity pass (SPEC.md section 6 / Task 2): Sprites.drawEntities
        // replays $115e0 as a post-terrain far->near pass, byte-exact against
        // tools/pm_render_ref.py draw_entities. The records in entities.json are
        // baked for the mission-1 start pose, so only draw them when the live
        // camera is at that pose. drawEntities writes into `buf` in the same
        // RAW $3f364 coordinate space Fill.walk uses, so the XInset shift below
        // then places terrain and sprites together.
        bool entPose = _camX == _entCamX && _camY == _entCamY && _yawSteps * 16 == _entYaw;
        if (entPose && _entRecs.Length > 0)
        {
            var ectx = new Sprites.EntityCtx(
                _entYaw, _entAnim, _entSelGroup, _entTileOff, _entRotPhase,
                _sheet33, _sheetProp, System.Array.Empty<byte>());
            Sprites.drawEntitiesArr(buf, ectx, corners, _camX, _camY, _entRecs);
        }

        // Fill.Buffer is in RAW $3f364 coordinates (0..255, same space $ef62's
        // own clip checks) -- Projection.fs does NOT add the +64px HUD-strip
        // inset (SPEC.md 3 "Draw inset": screenX = $3f364.sx + 64, applied at
        // $e420's own draw pointer, not baked into the vertex/accumulator).
        // Reading buf at (x - XInset) here does the same shift the real
        // hardware's $e3e2 pointer offset does (85th pass -- previously this
        // read buf at (x,y) directly, rendering the terrain 64px too far left
        // and leaving the true right ~64px of the window always blank).
        const int XInset = 64;
        var img = Image.CreateEmpty(Fill.ScreenWidth, Fill.ScreenHeight, false, Image.Format.Rgb8);
        for (int y = 0; y < Fill.ScreenHeight; y++)
        {
            for (int x = 0; x < Fill.ScreenWidth; x++)
            {
                int bx = x - XInset;
                bool covered = bx >= 0 && bx < Fill.ScreenWidth && buf.Covered[y * Fill.ScreenWidth + bx];
                img.SetPixel(x, y, covered ? _palette[buf.Index[y * Fill.ScreenWidth + bx] & 0x0f] : Uncovered);
            }
        }
        // HUD world minimap (SPEC.md section 9 item 6): the game bakes this into
        // the $78000 master once, via $e6ee, as a 1:1 per-cell plot at screen
        // origin (1, 6). Here it is redrawn every frame from the type plane
        // (the from-scratch stand-in for $13b9a's $418ae buffer -- ~94% of the
        // baked pixels). A real port would also overlay the camera viewport box
        // and the lord dots (an event-driven pass, not yet reversed).
        for (int wy = 0; wy < Terrain.Height; wy++)
        for (int wx = 0; wx < Terrain.Width; wx++)
        {
            int sx = wx + Terrain.MinimapOriginX, sy = wy + Terrain.MinimapOriginY;
            if (sx < 0 || sx >= Fill.ScreenWidth || sy < 0 || sy >= Fill.ScreenHeight)
                continue;
            int idx = Terrain.minimapPaletteIndex(_map.TypeAt(wx, wy));
            img.SetPixel(sx, sy, _palette[idx & 0x0f]);
        }
        // camera window outline on the minimap: cells [camX..camX+7] x [camY..camY+7]
        for (int d = 0; d < 8; d++)
        {
            foreach (var (cx, cy) in new[] {
                (_camX + d, _camY), (_camX + d, _camY + 7),
                (_camX, _camY + d), (_camX + 7, _camY + d) })
            {
                int sx = cx + Terrain.MinimapOriginX, sy = cy + Terrain.MinimapOriginY;
                if (sx >= 0 && sx < Fill.ScreenWidth && sy >= 0 && sy < Fill.ScreenHeight)
                    img.SetPixel(sx, sy, _palette[0]); // black box, like the game's
            }
        }

        // (The per-cell entity pass ran above, right after Fill.walk, so its
        // sprites are already in `buf` and go through the same XInset blit.)

        _rect.Texture = ImageTexture.CreateFromImage(img);
        int yaw = _yawSteps * 16;
        int quadrant = (((yaw + 8) >> 5) & 6) >> 1;
        _label.Text = $"camCell ({_camX},{_camY}) yaw {_yawSteps}/16 (${yaw:x2}, {QuadrantNames[quadrant]}) — "
                      + $"{(entPose ? _entRecs.Length + " entities" : "entities: pan to start pose")} — "
                      + "arrows pan, PgUp/PgDn rotate";
    }
}
