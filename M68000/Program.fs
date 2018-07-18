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
type AtartSt(romPath) =
    let rom = IO.File.ReadAllBytes(romPath)
    let ram = Array.create 1048576 0uy
    let mmu = MMU(rom, ram)
    let mutable cpu = Cpu.Create(mmu)
    
    member x.Reset() = cpu <- cpu.Reset()
    member x.Rom = rom
    
    member x.Step() =
        cpu <- cpu.Step()
        //printfn "%A" x
    
    member x.Debug =
       sprintf """
-------------
CPU Registers
%A
-------------""" cpu

    member x.Cpu = cpu

#if INTERACTIVE 
let st = AtartSt("TOS100UK.IMG")
st.Reset()
for _ in 1..100 do
    st.Step()
#else
module Main =
    [<EntryPoint>]
    let main arg=
        let st = AtartSt("TOS100UK.IMG")
        st.Reset()
        for i in 1..20 do st.Step()
        let rec loop() =
            match Console.ReadLine() with
            | "help" | "h" -> printfn "s = step, r = print registers, q = quit, help = this"
            | "step" | "s" ->
                st.Step()
                loop()
            | "registers" | "r" ->
                printfn "%s" st.Debug
                loop()
            | "quit" | "q" -> ()
            | _ -> ()
        loop()
        0   
#endif