#if INTERACTIVE
#load "Extensions.fs"
#load "MMU.fs"
#load "Instructions.fs"
#load "68k.fs"
open Atari
#else
namespace Atari
#endif

open System
open Bits
open Instructions

[<StructuredFormatDisplay("{Debug}")>]
type AtartSt(romPath: string) =
    let rom = IO.File.ReadAllBytes(romPath)
    let mmu = MMU(rom)
    let mutable cpu = Cpu.Create(mmu)
    
    member x.Reset() =
        cpu <- cpu.Reset()
    member x.Rom =
        rom
    
    member x.Step() =
        try
            cpu <- cpu.Step()
        with e ->
            //Diagnostics for implementing the next instruction: the opcode word, its common
            //sub-fields (most 68k formats split a word into these positions, though which fields
            //are meaningful depends on the instruction family - cross-check against the relevant
            //active pattern in Instructions.fs), and the raw words following it (covers immediate
            //values/displacements without a separate ROM read).
            let pc = uint32 cpu.PC
            let opcode = cpu.MMU.ReadWord pc
            let nextWords = [ for i in 1..5 -> cpu.MMU.ReadWord (pc + uint32 (i * 2)) ]
            eprintfn "Step failed at PC=$%08x" cpu.PC
            eprintfn "  opcode  $%04x  %s" opcode (int16 opcode).toBits
            eprintfn "  fields  [15-12]=%x [11-9]=%x [8-6]=%x [5-3]=%x [2-0]=%x   size[13-12]=%x"
                ((opcode >>> 12) &&& 0xf) ((opcode >>> 9) &&& 0x7) ((opcode >>> 6) &&& 0x7)
                ((opcode >>> 3) &&& 0x7) (opcode &&& 0x7) ((opcode >>> 12) &&& 0x3)
            eprintfn "  next words (PC+2, PC+4, ...): %s" (nextWords |> List.map (sprintf "$%04x") |> String.concat " ")
            eprintfn "  %s" e.Message
            eprintfn "%A" cpu
            reraise()
        //printfn "%A" x
    
    member x.Debug =
       sprintf """
-------------
CPU Registers
%A
-------------""" cpu

    member x.Cpu = cpu

    member x.DumpMemory (addr: uint32) (length: int) =
        String.concat " " [ for i in 0 .. length - 1 -> sprintf "%02x" (cpu.MMU.ReadByte (addr + uint32 i)) ]

#if INTERACTIVE
let st = AtartSt("TOS100UK.IMG")
st.Reset()
for _ in 1..100 do
    st.Step()
#else
module Main =
    [<EntryPoint>]
    let main argv =
        let st = AtartSt("TOS100UK.IMG")
        st.Reset()
        match argv with
        | [| stepsArg |] ->
            //Non-interactive mode, e.g. `dotnet run --no-build -- 20000`: run N steps (or until
            //an unimplemented instruction fails - Step() prints diagnostics and reraises) then
            //exit. No stdin required, so this can be driven from a plain shell command with no
            //piping and no risk of hanging on Console.ReadLine if the run completes cleanly.
            let steps = int stepsArg
            for _ in 1 .. steps do st.Step()
            0
        | _ ->
            for i in 1..20000 do st.Step()
            let rec loop() =
                let input = Console.ReadLine()
                let parts =
                    if isNull input then [||]
                    else input.Split(' ') |> Array.filter (fun s -> s <> "")
                match parts with
                | [| "help" |] | [| "h" |] ->
                    printfn "s [n] = step (n times, default 1), r = print registers, m <hexaddr> <len> = dump memory bytes, q = quit, help = this"
                    loop()
                | [| "step" |] | [| "s" |] ->
                    st.Step()
                    loop()
                | [| "step"; n |] | [| "s"; n |] ->
                    for _ in 1 .. int n do st.Step()
                    loop()
                | [| "registers" |] | [| "r" |] ->
                    printfn "%s" st.Debug
                    loop()
                | [| "m"; addr; len |] ->
                    printfn "%s" (st.DumpMemory (Convert.ToUInt32(addr, 16)) (int len))
                    loop()
                | [| "quit" |] | [| "q" |] ->
                    ()
                | _ ->
                    ()
            loop()
            0
#endif