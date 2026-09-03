using Godot;
using PmLogic;

namespace PowerMongerPort;

/// <summary>
/// Skeleton node: loads assets/terrain.bin + tables.json via the F# logic lib,
/// builds one ArrayMesh heightfield of the mission-1 island, and shades each
/// vertex by the flat height ramp. This is the toolchain proof, NOT the full
/// renderer (no dither, no sprites, no per-frame reprojection) — see
/// reversing/powermonger/port/SPEC.md.
/// </summary>
public partial class TerrainView : Node3D
{
    [Export] public string AssetsDir = "res://assets";
    [Export] public int CamCellX = 36; // $4bb3a - $57ffc
    [Export] public int CamCellY = 47; // $4bb3c - $57ffc

    private static readonly Color[] Palette =
    {
        // assets/palette.json, dominant palette, 3-bit-per-gun expansion
        new(0, 0, 0), new(.28f, .28f, .14f), new(.43f, .43f, .28f), new(.57f, .57f, .43f),
        new(.71f, .71f, .57f), new(.86f, .86f, .71f), new(.43f, .28f, .14f), new(.57f, .43f, .14f),
        new(.71f, .28f, 0), new(.71f, .57f, .14f), new(.86f, .86f, .14f), new(.57f, .71f, .14f),
        new(.43f, .57f, .14f), new(.28f, .43f, .14f), new(0, .28f, .43f), new(.28f, .43f, .57f),
    };

    public override void _Ready()
    {
        var raw = FileAccess.GetFileAsBytes($"{AssetsDir}/terrain.bin");
        if (raw.Length == 0)
        {
            GD.PushError($"terrain.bin not found under {AssetsDir}; run tools/pm_export.py");
            return;
        }

        Terrain.Map map = Terrain.parse(raw);
        var bb = Terrain.islandBBox(map);
        int x0 = bb.Item1, y0 = bb.Item2, x1 = bb.Item3, y1 = bb.Item4;
        GD.Print($"terrain loaded: island cells x{x0}..{x1} y{y0}..{y1}");

        AddChild(BuildMesh(map, x0, y0, x1, y1));
        AddChild(new Camera3D
        {
            Position = new Vector3((x0 + x1) * 0.5f, 40f, (y1) + 25f),
            // look down the -Z-ish axis at the island centre
            Rotation = new Vector3(Mathf.DegToRad(-45f), 0, 0),
        });
        AddChild(new DirectionalLight3D { Rotation = new Vector3(Mathf.DegToRad(-55f), 0.6f, 0) });
    }

    private static MeshInstance3D BuildMesh(Terrain.Map map, int x0, int y0, int x1, int y1)
    {
        var st = new SurfaceTool();
        st.Begin(Mesh.PrimitiveType.Triangles);

        float HeightAt(int x, int y) => map.HeightAt(x, y) * 0.12f;
        Color ColAt(int x, int y) =>
            Palette[Terrain.flatPaletteIndex(map.HeightAt(x, y)) & 0x0f];

        for (int y = y0; y < y1; y++)
        {
            for (int x = x0; x < x1; x++)
            {
                // two triangles per cell, matching $f898's far->near quad split
                Vector3 TL = new(x, HeightAt(x, y), y);
                Vector3 TR = new(x + 1, HeightAt(x + 1, y), y);
                Vector3 BL = new(x, HeightAt(x, y + 1), y + 1);
                Vector3 BR = new(x + 1, HeightAt(x + 1, y + 1), y + 1);

                st.SetColor(ColAt(x, y)); st.AddVertex(TL);
                st.SetColor(ColAt(x + 1, y)); st.AddVertex(TR);
                st.SetColor(ColAt(x, y + 1)); st.AddVertex(BL);

                st.SetColor(ColAt(x + 1, y)); st.AddVertex(TR);
                st.SetColor(ColAt(x + 1, y + 1)); st.AddVertex(BR);
                st.SetColor(ColAt(x, y + 1)); st.AddVertex(BL);
            }
        }

        st.GenerateNormals();
        var mat = new StandardMaterial3D
        {
            VertexColorUseAsAlbedo = true,
            Roughness = 1.0f,
        };
        var mi = new MeshInstance3D { Mesh = st.Commit(), MaterialOverride = mat };
        return mi;
    }
}
