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
/// Scope: the terrain layer only, quadrant 3 (yaw fixed at $f0, the only grid
/// walk ported so far — see SPEC.md section 4 "the yaw-quadrant grid walk").
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
    [Export] public int PixelScale = 3;

    private static readonly Color Uncovered = new(1f, 0f, 1f); // magenta, matches render_faithful.png

    private Terrain.Map _map = null!;  // set in _Ready, before any other use
    private byte[] _dither = System.Array.Empty<byte>();
    private Color[] _palette = new Color[16];
    private readonly PmProjection.Params _proj = PmProjection.Params.Mission1; // Eye 320, Horizon 130, Zoom 21, yaw=0xf0 (quadrant 3), Half 4

    private TextureRect _rect = null!; // set in _Ready
    private Label _label = null!;      // set in _Ready
    private int _camX, _camY;

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

        _camX = Mathf.Clamp(CamCellX, MinCamX, MaxCamX);
        _camY = Mathf.Clamp(CamCellY, MinCamY, MaxCamY);

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
        if (dx == 0 && dy == 0) return;
        int nx = Mathf.Clamp(_camX + dx, MinCamX, MaxCamX);
        int ny = Mathf.Clamp(_camY + dy, MinCamY, MaxCamY);
        if (nx == _camX && ny == _camY) return;
        _camX = nx;
        _camY = ny;
        RenderFrame();
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
        var corners = PmProjection.projectGrid(_proj, _map, _camX, _camY);
        var buf = Fill.Buffer.Create();
        Fill.walkQ3(buf, _dither, corners, _map, _camX, _camY, tick: 0);

        var img = Image.CreateEmpty(Fill.ScreenWidth, Fill.ScreenHeight, false, Image.Format.Rgb8);
        for (int y = 0; y < Fill.ScreenHeight; y++)
        {
            for (int x = 0; x < Fill.ScreenWidth; x++)
            {
                int i = y * Fill.ScreenWidth + x;
                img.SetPixel(x, y, buf.Covered[i] ? _palette[buf.Index[i] & 0x0f] : Uncovered);
            }
        }
        _rect.Texture = ImageTexture.CreateFromImage(img);
        _label.Text = $"camCell ({_camX},{_camY}) — arrow keys pan; yaw fixed to quadrant 3 ($f0)";
    }
}
