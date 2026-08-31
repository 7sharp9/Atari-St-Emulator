/// Live SDL2 window: renders the Atari ST shifter output and feeds real host keyboard/mouse
/// input back to TOS as IKBD serial packets. Opt-in (`dotnet run -- window`); the headless
/// step/snapshot/REPL workflow is untouched and stays the default.
///
/// SDL2 via Silk.NET.SDL - the same library family real ST emulators (Hatari) build on. A single
/// streaming ARGB texture holds the decoded framebuffer; the ST's tiny 32KB screen and its
/// blitter (emulated in F#, not here) never stress it. The three shifter modes are decoded with
/// the same interleaved-bitplane logic as tools/screendump.py.
module Video

open System
open System.Diagnostics
open Microsoft.FSharp.NativeInterop
open Silk.NET.SDL

#nowarn "9" // nativeptr / fixed

// ST video is always rendered into a fixed 640x400 ARGB surface: low-res doubles both axes,
// med-res doubles vertically, high-res is 1:1. Keeps the window size constant across mode
// changes (the desktop switches modes when you change resolution from the menu).
let private TexW = 640
let private TexH = 400

/// Host physical-key -> Atari ST scancode. ST make code = this value, break code = value ||| 0x80.
/// Keyed by Silk.NET.SDL.Scancode (physical position, so it survives keyboard-layout differences
/// as far as the position goes). Covers the main typing area, the arrow/edit cluster, the
/// function row and the ST-specific Help/Undo keys; anything not listed is simply ignored.
let private scancodeMap =
    dict [
        Scancode.ScancodeEscape, 0x01uy
        Scancode.Scancode1, 0x02uy; Scancode.Scancode2, 0x03uy; Scancode.Scancode3, 0x04uy
        Scancode.Scancode4, 0x05uy; Scancode.Scancode5, 0x06uy; Scancode.Scancode6, 0x07uy
        Scancode.Scancode7, 0x08uy; Scancode.Scancode8, 0x09uy; Scancode.Scancode9, 0x0Auy
        Scancode.Scancode0, 0x0Buy
        Scancode.ScancodeMinus, 0x0Cuy; Scancode.ScancodeEquals, 0x0Duy
        Scancode.ScancodeBackspace, 0x0Euy; Scancode.ScancodeTab, 0x0Fuy
        Scancode.ScancodeQ, 0x10uy; Scancode.ScancodeW, 0x11uy; Scancode.ScancodeE, 0x12uy
        Scancode.ScancodeR, 0x13uy; Scancode.ScancodeT, 0x14uy; Scancode.ScancodeY, 0x15uy
        Scancode.ScancodeU, 0x16uy; Scancode.ScancodeI, 0x17uy; Scancode.ScancodeO, 0x18uy
        Scancode.ScancodeP, 0x19uy
        Scancode.ScancodeLeftbracket, 0x1Auy; Scancode.ScancodeRightbracket, 0x1Buy
        Scancode.ScancodeReturn, 0x1Cuy
        Scancode.ScancodeLctrl, 0x1Duy; Scancode.ScancodeRctrl, 0x1Duy
        Scancode.ScancodeA, 0x1Euy; Scancode.ScancodeS, 0x1Fuy; Scancode.ScancodeD, 0x20uy
        Scancode.ScancodeF, 0x21uy; Scancode.ScancodeG, 0x22uy; Scancode.ScancodeH, 0x23uy
        Scancode.ScancodeJ, 0x24uy; Scancode.ScancodeK, 0x25uy; Scancode.ScancodeL, 0x26uy
        Scancode.ScancodeSemicolon, 0x27uy; Scancode.ScancodeApostrophe, 0x28uy
        Scancode.ScancodeGrave, 0x29uy
        Scancode.ScancodeLshift, 0x2Auy; Scancode.ScancodeBackslash, 0x2Buy
        Scancode.ScancodeZ, 0x2Cuy; Scancode.ScancodeX, 0x2Duy; Scancode.ScancodeC, 0x2Euy
        Scancode.ScancodeV, 0x2Fuy; Scancode.ScancodeB, 0x30uy; Scancode.ScancodeN, 0x31uy
        Scancode.ScancodeM, 0x32uy
        Scancode.ScancodeComma, 0x33uy; Scancode.ScancodePeriod, 0x34uy; Scancode.ScancodeSlash, 0x35uy
        Scancode.ScancodeRshift, 0x36uy
        Scancode.ScancodeLalt, 0x38uy; Scancode.ScancodeRalt, 0x38uy
        Scancode.ScancodeSpace, 0x39uy; Scancode.ScancodeCapslock, 0x3Auy
        Scancode.ScancodeF1, 0x3Buy; Scancode.ScancodeF2, 0x3Cuy; Scancode.ScancodeF3, 0x3Duy
        Scancode.ScancodeF4, 0x3Euy; Scancode.ScancodeF5, 0x3Fuy; Scancode.ScancodeF6, 0x40uy
        Scancode.ScancodeF7, 0x41uy; Scancode.ScancodeF8, 0x42uy; Scancode.ScancodeF9, 0x43uy
        Scancode.ScancodeF10, 0x44uy
        Scancode.ScancodeHome, 0x47uy; Scancode.ScancodeUp, 0x48uy
        Scancode.ScancodeLeft, 0x4Buy; Scancode.ScancodeRight, 0x4Duy; Scancode.ScancodeDown, 0x50uy
        Scancode.ScancodeInsert, 0x52uy; Scancode.ScancodeDelete, 0x53uy
        Scancode.ScancodeEnd, 0x61uy       // ST Undo
        Scancode.ScancodePagedown, 0x62uy  // ST Help
    ]

/// Host physical-key -> joystick-0 state-byte bit. An IKBD joystick report is `$FE` (joystick 0)
/// or `$FF` (joystick 1) followed by one state byte: bit0 up, bit1 down, bit2 left, bit3 right,
/// bit7 fire. Super Sprint's own IKBD handler ($104b6) stashes that byte in its joytable, and the
/// game reads a raw joystick channel (2 = joy0) for players 1-2 - the only way a window player
/// gets an accelerate input, since the keyboard synth (channel 0) has no way to reach it.
///
/// In Super Sprint the fire bit ($80) is the accelerator pedal (verified in-race: holding it
/// drives the joined car off the grid and round the circuit, the direction bits steer), so Up is
/// mapped to fire rather than to the largely-unused up bit. The arrow keys still also emit their
/// ST cursor scancodes via scancodeMap; harmless, nothing on channel 0 uses them. Each host key
/// owns a distinct bit so the keyup edge can clear exactly that bit.
let private joyBitMap =
    dict [
        Scancode.ScancodeUp, 0x80uy      // accelerator pedal (Super Sprint reads fire as the gas)
        Scancode.ScancodeDown, 0x02uy    // joystick "down" (brake / reverse where a game uses it)
        Scancode.ScancodeLeft, 0x04uy
        Scancode.ScancodeRight, 0x08uy
    ]

let private gun3 (v: int) = (v &&& 7) * 255 / 7
let private gun4 (v: int) = (v &&& 0xF) * 255 / 15

/// One $0RGB shifter palette word -> (r,g,b). STF is 3 bits/gun (near-linear DAC); a gun value
/// above 7 means an STE 4-bit entry, handled linearly too. Matches tools/screendump.py.
let private paletteColour (word: int) =
    let r, g, b = (word >>> 8) &&& 0xF, (word >>> 4) &&& 0xF, word &&& 0xF
    if r > 7 || g > 7 || b > 7 then gun4 r, gun4 g, gun4 b
    else gun3 r, gun3 g, gun3 b

/// Decodes the current shifter framebuffer into `pixels` (TexW*TexH*4 bytes, ARGB8888 = B,G,R,A
/// in memory). Reads base from _v_bas_ad ($44E), mode from $FFFF8260 & 3, palette from the 16
/// words at $FFFF8240.
let decodeFramebuffer (mmu: Atari.MMU) (pixels: byte[]) =
    let baseAddr = uint32 (mmu.ReadLong 0x44Eu)
    let rez = int (mmu.ReadByte 0xFFFF8260u) &&& 3
    let planes = match rez with 0 -> 4 | 1 -> 2 | _ -> 1
    let palette =
        if rez = 2 then [| (255, 255, 255); (0, 0, 0) |]
        else Array.init 16 (fun i -> paletteColour (int (uint16 (mmu.ReadWord (0xFFFF8240u + uint32 (i * 2))))))
    let srcW = if rez = 0 then 320 else 640
    let srcH = if rez = 2 then 400 else 200
    let rowBytes = srcW * planes / 8
    let put dstX dstY (r, g, b) =
        let o = (dstY * TexW + dstX) * 4
        pixels.[o] <- byte b
        pixels.[o + 1] <- byte g
        pixels.[o + 2] <- byte r
        pixels.[o + 3] <- 255uy
    for sy in 0 .. srcH - 1 do
        let rowBase = baseAddr + uint32 (sy * rowBytes)
        for sx in 0 .. srcW - 1 do
            let wordIdx = sx / 16
            let bit = 15 - (sx % 16)
            let mutable idx = 0
            for p in 0 .. planes - 1 do
                let w = int (uint16 (mmu.ReadWord (rowBase + uint32 (wordIdx * 2 * planes + p * 2))))
                idx <- idx ||| (((w >>> bit) &&& 1) <<< p)
            let colour = palette.[idx]
            // Scale the native mode up into the fixed 640x400 surface.
            match rez with
            | 0 -> // 320x200 -> 2x2
                put (sx * 2) (sy * 2) colour
                put (sx * 2 + 1) (sy * 2) colour
                put (sx * 2) (sy * 2 + 1) colour
                put (sx * 2 + 1) (sy * 2 + 1) colour
            | 1 -> // 640x200 -> 1x2
                put sx (sy * 2) colour
                put sx (sy * 2 + 1) colour
            | _ -> put sx sy colour // 640x400 1:1

let inline private nullPtr<'T when 'T: unmanaged> : nativeptr<'T> = NativePtr.ofNativeInt 0n

/// Opens the window and runs the emulator/render/input loop until the window is closed. `step`
/// advances the CPU one instruction; `stepCount` reads the emulator's running instruction total
/// and `instructionsPerFrame` is one emulated ~50 Hz video frame (see Program.fs's emulated-time
/// block) - together they let the render loop run exactly one frame per host frame and decode the
/// framebuffer on the VBL boundary; `mmu` reads the framebuffer and enqueues IKBD input.
let run (step: unit -> unit) (stepCount: unit -> uint64) (instructionsPerFrame: int) (mmu: Atari.MMU) =
    let sdl = Sdl.GetApi()
    if sdl.Init(Sdl.InitVideo ||| Sdl.InitEvents) <> 0 then
        failwithf "SDL_Init failed: %s" (sdl.GetErrorS())

    let scale = 2
    let window =
        sdl.CreateWindow(
            "Atari ST",
            Sdl.WindowposCentered, Sdl.WindowposCentered,
            TexW * scale, TexH * scale,
            uint32 WindowFlags.Shown)
    let renderer = sdl.CreateRenderer(window, -1, uint32 (RendererFlags.Accelerated ||| RendererFlags.Presentvsync))
    let texture =
        sdl.CreateTexture(renderer, uint32 PixelFormatEnum.Argb8888, int TextureAccess.Streaming, TexW, TexH)

    // Relative mouse mode: SDL reports pure deltas, which is exactly what an IKBD relative mouse
    // packet carries. The pointer is drawn by TOS itself, in the framebuffer.
    sdl.SetRelativeMouseMode(SdlBool.True) |> ignore

    let pixels = Array.zeroCreate<byte> (TexW * TexH * 4)
    let mutable running = true
    let mutable ev = Unchecked.defaultof<Event>

    // Accumulated mouse motion for the current frame - coalesced into as few IKBD packets as the
    // -128..127 per-axis range allows, sent once per frame rather than per SDL event.
    let mutable mdx = 0
    let mutable mdy = 0
    let mutable mouseButtons = 0 // bit0 = right, bit1 = left (IKBD relative-packet header bits)

    // Joystick-0 state byte (see joyBitMap) plus a dirty flag. Like the mouse, the real IKBD only
    // reports joystick 0 on a state change, so a packet is emitted only when a mapped key edge
    // actually changed a bit, coalesced to at most one per frame in the front-loaded flush below.
    let mutable joyState = 0uy
    let mutable joyDirty = false

    let sendJoyPacket () =
        if joyDirty then
            mmu.EnqueueIkbd [| 0xFEuy; joyState |]
            joyDirty <- false

    // `force` = a button-state change happened, so a packet must reach TOS even with zero motion;
    // the per-frame flush passes false so an idle mouse produces no traffic (the real IKBD only
    // reports on movement or a button edge - a 50Hz stream of F8 00 00 packets is not hardware
    // behaviour and needlessly wakes the ISR + MFP interrupt every frame).
    let sendMousePacket (force: bool) =
        if mdx <> 0 || mdy <> 0 || force then
            let mutable rx = mdx
            let mutable ry = mdy
            // Always emit at least one packet (that is the point of `force`); then keep emitting
            // while either axis still has delta that didn't fit in the -128..127 byte range.
            let mutable first = true
            while first || rx <> 0 || ry <> 0 do
                first <- false
                let cx = max -128 (min 127 rx)
                let cy = max -128 (min 127 ry)
                mmu.EnqueueIkbd [| byte (0xF8 ||| mouseButtons); byte (sbyte cx); byte (sbyte cy) |]
                rx <- rx - cx
                ry <- ry - cy
            mdx <- 0
            mdy <- 0

    let pollEvents () =
        while sdl.PollEvent(&ev) = 1 do
            match enum<EventType> (int ev.Type) with
            | EventType.Quit -> running <- false
            | EventType.Keydown ->
                if ev.Key.Repeat = 0uy then
                    let sc = ev.Key.Keysym.Scancode
                    if sc = Scancode.ScancodeF12 then running <- false
                    else
                        match scancodeMap.TryGetValue sc with
                        | true, st -> mmu.EnqueueIkbd [| st |]
                        | _ -> ()
                        match joyBitMap.TryGetValue sc with
                        | true, bit when joyState &&& bit = 0uy -> joyState <- joyState ||| bit; joyDirty <- true
                        | _ -> ()
            | EventType.Keyup ->
                let sc = ev.Key.Keysym.Scancode
                match scancodeMap.TryGetValue sc with
                | true, st -> mmu.EnqueueIkbd [| st ||| 0x80uy |]
                | _ -> ()
                match joyBitMap.TryGetValue sc with
                | true, bit when joyState &&& bit <> 0uy -> joyState <- joyState &&& ~~~bit; joyDirty <- true
                | _ -> ()
            | EventType.Mousemotion ->
                mdx <- mdx + ev.Motion.Xrel
                mdy <- mdy + ev.Motion.Yrel
            | EventType.Mousebuttondown ->
                if int ev.Button.Button = int Sdl.ButtonLeft then mouseButtons <- mouseButtons ||| 0x02
                elif int ev.Button.Button = int Sdl.ButtonRight then mouseButtons <- mouseButtons ||| 0x01
                sendMousePacket true
            | EventType.Mousebuttonup ->
                if int ev.Button.Button = int Sdl.ButtonLeft then mouseButtons <- mouseButtons &&& ~~~0x02
                elif int ev.Button.Button = int Sdl.ButtonRight then mouseButtons <- mouseButtons &&& ~~~0x01
                sendMousePacket true
            | _ -> ()

    let sw = Stopwatch.StartNew()
    // One host frame == one emulated video frame. Run instructions up to the next VBL boundary
    // (stepCount() a multiple of instructionsPerFrame), then decode.
    //
    // Cursor tearing: TOS redraws the VDI mouse cursor (save-under, mask-clear to colour 0, then
    // the arrow shape) whenever it processes a mouse packet - a multi-thousand-instruction BitBlt.
    // If a packet is delivered late in the frame the redraw can still be in progress at the VBL
    // boundary, so the decode catches a half-drawn cursor (a white mask block, colour index 0).
    // Fix: deliver ALL accumulated host mouse motion once, at the very start of the frame, so the
    // redraw happens with the whole rest of the frame (~10k instructions) as settling runway
    // before the capture. Costs up to one frame (20 ms) of pointer latency, which is what real
    // hardware feels like anyway. Events are still polled every slice so keyboard/quit stay
    // responsive; only the mouse flush is front-loaded.
    let slices = 6
    let ipf = uint64 instructionsPerFrame
    let sliceSteps = uint64 (max 1 (instructionsPerFrame / slices))
    let frameMs = 20.0 // 50 Hz

    while running do
        let frameStart = sw.Elapsed.TotalMilliseconds

        // Next VBL boundary at or after the current position (handles a resumed snapshot whose
        // stepCount is not frame-aligned - the first frame is just short).
        let target = (stepCount() / ipf + 1UL) * ipf
        pollEvents ()
        sendMousePacket false // front-loaded: see the tearing note above
        sendJoyPacket ()      // at most one joystick-0 report per frame, only on a state change
        while running && stepCount() < target do
            pollEvents ()
            let sliceEnd = min target (stepCount() + sliceSteps)
            while stepCount() < sliceEnd do step ()

        decodeFramebuffer mmu pixels
        use p = fixed pixels
        sdl.UpdateTexture(texture, nullPtr<Silk.NET.Maths.Rectangle<int>>, NativePtr.toVoidPtr p, TexW * 4) |> ignore
        sdl.RenderClear(renderer) |> ignore
        sdl.RenderCopy(renderer, texture, nullPtr<Silk.NET.Maths.Rectangle<int>>, nullPtr<Silk.NET.Maths.Rectangle<int>>) |> ignore
        sdl.RenderPresent(renderer)

        let elapsed = sw.Elapsed.TotalMilliseconds - frameStart
        if elapsed < frameMs then Threading.Thread.Sleep(int (frameMs - elapsed))

    sdl.DestroyTexture(texture)
    sdl.DestroyRenderer(renderer)
    sdl.DestroyWindow(window)
    sdl.Quit()
