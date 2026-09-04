namespace PmLogic

/// Port of PowerMonger's grid-corner projection ($fecc / $ff7c).
/// See ../../SPEC.md section 3. Faithful to the 68000 maths (the >>15 after the
/// rotate keeps rx/ry in world-pixel units); a modern renderer would instead
/// feed camera + heightfield to a vertex shader.
module Projection =

    /// Projection parameters, from assets/tables.json -> projection.
    type Params =
        { Eye: float          // $ff98, 320
          Horizon: float      // $ff96, 130
          Zoom: float         // $ff9c, 21 at zoom index 4
          YawSteps: int       // $ff9a >> 4, 0..15
          Half: int }         // grid half-extent, 4 at zoom index 4

        static member Mission1 =
            { Eye = 320.0; Horizon = 130.0; Zoom = 21.0; YawSteps = 15; Half = 4 }

        /// C#-friendly copy-with (F#'s `{ p with ... }` isn't callable from C#).
        member p.WithYaw(yawSteps: int) = { p with YawSteps = yawSteps }

    let private deg2rad d = d * System.Math.PI / 180.0

    /// theta = yaw * 1.40625 deg  (the $13f8a table is a plain sine table).
    let yawAngle (p: Params) = deg2rad (float (p.YawSteps * 16) * 1.40625)

    type Corner = { X: float; Y: float }

    /// Project one grid vertex. col,row are relative to the camera cell,
    /// each in -Half .. +Half. h = control-plane height at that cell.
    /// hbias = min control height over the visible window (recomputed per frame).
    let projectVertex (p: Params) (theta: float) (hbias: int) (col: int) (row: int) (h: int) : Corner =
        let sinT = sin theta
        let cosT = cos theta
        let z = ((h - hbias) * int p.Zoom) >>> 4 |> float
        let c = float col * p.Zoom
        let r = float row * p.Zoom
        // rotate by -theta  ($ff36..$ff4e):  rx = (c*Q - r*P)>>15, P=32768 sinT, Q=32768 cosT
        let rx = c * cosT - r * sinT
        let ry = r * cosT + c * sinT
        let d = p.Eye - ry
        let d = if d <= 1.0 then 1.0 else d
        let sx = rx * p.Eye / d
        let sy = (z - p.Horizon) * p.Eye / d + p.Horizon
        { X = sx + 128.0; Y = 124.0 - sy }

    /// Project the whole visible grid. Returns corners indexed [gr, gc],
    /// gr/gc in 0 .. 2*Half. camX,camY = camera cell (already minus $57ffc).
    let projectGrid (p: Params) (m: Terrain.Map) (camX: int) (camY: int) : Corner[,] =
        let n = 2 * p.Half + 1
        let theta = yawAngle p
        // dynamic height bias
        let mutable hbias = 255
        for gr in 0 .. n - 1 do
            for gc in 0 .. n - 1 do
                let hh = m.ControlAt(camX + gc, camY + gr)
                if hh < hbias then hbias <- hh
        Array2D.init n n (fun gr gc ->
            let h = m.ControlAt(camX + gc, camY + gr)
            projectVertex p theta hbias (gc - p.Half) (gr - p.Half) h)
