namespace PmLogic

/// One iso frame as PowerMonger draws it: $f898's grid walk with $115e0
/// called inline per cell. For each cell, far -> near, the game draws the
/// cell's two terrain triangles and then every sprite in that cell's
/// $47970 bucket, before moving on to the next cell. Nearer terrain is
/// drawn later, so it covers farther sprites, and nearer sprites cover
/// farther terrain: the painter's algorithm, with no depth sort.
///
/// Sprites.drawEntities is the other order (every sprite after all the
/// terrain), kept because it is what tools/pm_render_ref.py does and the
/// 90th/91st cross-checks compare against it.
module Scene =

    /// One thing the renderer draws, in frame order. Each step carries its
    /// cell, so it can be drawn (or highlighted) on its own.
    type Step =
        | Triangle of cell: Fill.Cell * nth: int * tri: Fill.Tri     // nth = 1 or 2 within the cell
        | Sprite of cell: Fill.Cell * record: Sprites.EntityRec

    /// The cell a step belongs to.
    let cellOf step =
        match step with
        | Triangle(c, _, _) | Sprite(c, _) -> c

    /// Interleave each cell's sprites after its triangles, in the order the
    /// walk visits the cells. Records whose category has no frame to draw
    /// (see Sprites.entityFrame) are left out; records outside the visible
    /// 8x8 are never reached. Within a cell, records keep the order given,
    /// which is their bucket-chain order.
    let steps (ctx: Sprites.EntityCtx) (cells: Fill.Cell list) (recs: Sprites.EntityRec seq) : Step[] =
        let byCell =
            recs
            |> Seq.filter (fun r -> (Sprites.entityFrame ctx r).IsSome)
            |> Seq.groupBy (fun r -> r.Wcx, r.Wcy)
            |> dict
        [| for c in cells do
             yield Triangle(c, 1, c.First)
             yield Triangle(c, 2, c.Second)
             match byCell.TryGetValue((c.X, c.Y)) with
             | true, rs -> for r in rs -> Sprite(c, r)
             | _ -> () |]

    let private cornersOf (c: Fill.Cell) =
        let px (p: Projection.Corner) = int (System.Math.Round p.X), int (System.Math.Round p.Y)
        px c.Quad.C00, px c.Quad.C10, px c.Quad.C01, px c.Quad.C11

    /// Where a sprite step lands on its cell's four projected corners.
    let placement (ctx: Sprites.EntityCtx) (c: Fill.Cell) (r: Sprites.EntityRec) =
        let c00, c10, c01, c11 = cornersOf c
        Sprites.placeEntity ctx c00 c10 c01 c11 r

    /// Draw one step into `buf`. For a triangle, returns what $ef62 did with it.
    let drawStep (buf: Fill.Buffer) (dith: byte[]) (tick: int) (ctx: Sprites.EntityCtx) (step: Step) =
        match step with
        | Triangle(_, _, t) -> Some(Fill.drawTri buf dith tick t)
        | Sprite(c, r) ->
            let c00, c10, c01, c11 = cornersOf c
            Sprites.blitEntity buf ctx c00 c10 c01 c11 r
            None

    /// Draw the whole frame: terrain and sprites, in the game's order.
    let render (buf: Fill.Buffer) (dith: byte[]) (tick: int) (ctx: Sprites.EntityCtx)
               (corners: Projection.Corner[,]) (map: Terrain.Map)
               (camX: int) (camY: int) (yawSteps: int) (recs: Sprites.EntityRec seq) =
        steps ctx (Fill.plan corners map camX camY yawSteps) recs
        |> Array.iter (drawStep buf dith tick ctx >> ignore)
