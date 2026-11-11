/// The domain: Midwinter's island without the hardware. A cell is a height and a seed; a level is a
/// square grid of cells; the next level is a pure function of the one before. The game computes only a
/// 100 x 100 window of the finest level because it has 1 MB of RAM; here the whole island is a value,
/// and the game's window is a view onto it.
module Island

[<Struct>]
type Cell = { Height: int16; Seed: uint16 }

/// Rows then columns; level 0 is 50 x 50, each level doubles it, level 5 is 1600 x 1600.
type Grid = Cell[,]

module Cell =
    /// What the game reads past the edge of its data: the cleared longword $ffffffff.
    let outside = { Height = -1s; Seed = 0xffffus }

    /// The height the renderer uses ($1991a): the sea is flat at 0 and the shore is stretched into a step.
    let groundHeight (c: Cell) =
        match int c.Height with
        | h when h < 0 -> 0
        | h when h <= 9 -> (h + 1) * 24
        | h -> h + 250

// ---------------------------------------------------------------- from the 68000's memory

/// A grid as the game stores it: rows of big-endian (height.w, seed.w) longwords.
let readGrid (ram: byte[]) (addr: int) (size: int) : Grid =
    Array2D.init size size (fun r c ->
        let a = addr + 4 * (r * size + c)
        { Height = int16 (Heritage.word ram a); Seed = uint16 (Heritage.word ram (a + 2)) })

// ---------------------------------------------------------------- one new point ($285a)

/// A new cell from four parents. There is no random number generator: the seeds are summed, the sum's
/// low 16 bits are the noise and its carry leaks into the height (the game adds the four longwords),
/// the displacement grows with the height, so peaks are rougher than lowland, and `shift` halves the
/// noise at each finer level. The new seed is the sum XORed with the first parent's seed.
let mid (shift: int) (a: Cell) (b: Cell) (c: Cell) (d: Cell) : Cell =
    let seeds = int a.Seed + int b.Seed + int c.Seed + int d.Seed
    let height = int a.Height + int b.Height + int c.Height + int d.Height + (seeds >>> 16)
    let avg = int (int16 height) >>> 2
    let noise = int (int16 seeds) >>> shift
    let roughness = int (int16 (avg * 8 + 5000))
    let displacement = int (int16 ((noise * roughness) >>> 16))
    { Height = int16 (avg + displacement)
      Seed = uint16 ((seeds ^^^ int a.Seed) &&& 0x3fff) }

// ---------------------------------------------------------------- one level finer ($2ca6)

/// Diamond-square on the whole grid. Source cell S(r, c) lands at (2r, 2c); C is the centre of each
/// square of four; H the point between two neighbours on a row; V the point between two rows.
/// Outside the grid every cell is `Cell.outside`.
let refine (shift: int) (g: Grid) : Grid =
    let n = Array2D.length1 g
    let s r c = if r >= 0 && r < n && c >= 0 && c < n then g.[r, c] else Cell.outside
    let centres =
        Array2D.init (n + 1) (n + 1) (fun r c ->
            let r, c = r - 1, c - 1
            mid shift (s r c) (s r (c + 1)) (s (r + 1) c) (s (r + 1) (c + 1)))
    let centre r c = centres.[r + 1, c + 1]
    Array2D.init (2 * n) (2 * n) (fun y x ->
        let r, c = y / 2, x / 2
        match y % 2, x % 2 with
        | 0, 0 -> s r c
        | 0, _ -> mid shift (centre r c) (centre (r - 1) c) (s r c) (s r (c + 1))          // H
        | _, 1 -> centre r c                                                               // C
        | _ -> mid shift (centre r (c - 1)) (centre r c) (s r c) (s (r + 1) c))            // V

/// The noise shift each refinement uses: the game sets 4 for the whole island ($1999a) and adds one after
/// each zoom has refined ($199ec), so the first zoom refines at 4 as well.
let shifts = [ 4; 4; 5; 6; 7 ]

/// Every level of the island, coarsest first: file 37.2, then five refinements.
let levels (file372: Grid) : Grid list =
    List.scan (fun g shift -> refine shift g) file372 shifts

/// What the game holds in RAM: the 100 x 100 cells of a level whose top-left is `origin`.
let window (level: Grid) (originX: int, originY: int) : Grid =
    Array2D.init 100 100 (fun r c -> level.[originY + r, originX + c])
