// Headless Ghidra decompile of a relocated ST program image (tools/prg2img.py) into one C file.
// Seeds functions at the entry, every LINK A6 and every jsr/jmp abs.l target inside TEXT, so it
// suits compiled C (Alcyon, Lattice, Megamax, Pure C). Hand-written asm without LINK frames gets
// only the jsr targets; packed programs must be unpacked first (decompile a RAM dump instead).
//
//   "C:/Program Files/ghidra_12.1_PUBLIC/support/analyzeHeadless.bat" <projdir> <projname> \
//     -import prog.img -overwrite -processor 68000:BE:32:default -loader BinaryLoader \
//     -loader-baseAddr 0x<text> -scriptPath tools/ghidra -postScript DecompileAll.java \
//     0x<textlen> out.c [names.sym] [purge.txt] [traps.txt]
//
// names.sym : addr<TAB>name (the reversing/<game>/<game>.sym format); functions get renamed.
// purge.txt : "addr bytes name" - callee stack purge for runtime helpers that return through
//             their argument slots (Alcyon lmul/ldiv), which otherwise wreck stack tracking.
//             Every other function is set caller-clean (purge 0), the C convention on the ST.
// traps.txt : "addr name" - GEMDOS/BIOS/XBIOS wrappers, typed long name(short fn, ...).
// Example overrides: reversing/populous/py/ghidra/. About 20 s for a 90 KB program.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import java.io.*;
import java.util.*;

public class DecompileAll extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        long textLen = Long.decode(args[0]);
        String out = args[1];
        String symfile = args.length > 2 ? args[2] : null;
        Memory mem = currentProgram.getMemory();
        Address base = currentProgram.getMinAddress();
        // seed: entry + LINK A6 (0x4e56) at even offsets + jsr abs.l targets inside text
        TreeSet<Long> seeds = new TreeSet<>();
        seeds.add(0L);
        for (long o = 0; o + 6 <= textLen; o += 2) {
            int w = mem.getShort(base.add(o)) & 0xffff;
            if (w == 0x4e56) seeds.add(o);
            if (w == 0x4eb9 || w == 0x4ef9) {
                long t = (mem.getInt(base.add(o + 2)) & 0xffffffffL) - base.getOffset();
                if (t >= 0 && t < textLen && (t & 1) == 0) seeds.add(t);
            }
        }
        for (long s : seeds) {
            new DisassembleCommand(base.add(s), null, true).applyTo(currentProgram, monitor);
        }
        for (long s : seeds) {
            Address a = base.add(s);
            if (getFunctionAt(a) == null) new CreateFunctionCmd(a).applyTo(currentProgram, monitor);
        }
        // Alcyon C is caller-clean: every callee pops nothing (overridden below for the stack-return helpers)
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) f.setStackPurgeSize(0);
        // Alcyon C runtime helpers that return through their stack arg slots:
        // "addr purge name" lines; purge = bytes the callee pops besides the return address
        if (args.length > 3) {
            for (String line : java.nio.file.Files.readAllLines(new File(args[3]).toPath())) {
                String[] p = line.trim().split("\\s+");
                if (p.length < 3 || p[0].startsWith("#")) continue;
                Address a = toAddr(Long.parseLong(p[0], 16));
                Function f = getFunctionAt(a);
                if (f == null) { new CreateFunctionCmd(a).applyTo(currentProgram, monitor); f = getFunctionAt(a); }
                f.setStackPurgeSize(Integer.parseInt(p[1]));
                f.setName(p[2], ghidra.program.model.symbol.SourceType.USER_DEFINED);
            }
        }
        setAnalysisOption(currentProgram, "Decompiler Parameter ID", "true");
        analyzeChanges(currentProgram);
        if (symfile != null) {
            for (String line : java.nio.file.Files.readAllLines(new File(symfile).toPath())) {
                String[] p = line.trim().split("\\s+");
                if (p.length < 2 || p[0].startsWith("#")) continue;
                Address a = toAddr(Long.parseLong(p[0], 16));
                Function f = getFunctionAt(a);
                if (f != null) f.setName(p[1], ghidra.program.model.symbol.SourceType.USER_DEFINED);
                else createLabel(a, p[1], true);
            }
        }
        for (Function f : currentProgram.getFunctionManager().getFunctions(true))
            if (!f.getName().endsWith("_stk")) f.setStackPurgeSize(0);
        // varargs trap wrappers: "addr name" -> long name(short fn, ...)
        if (args.length > 4) {
            for (String line : java.nio.file.Files.readAllLines(new File(args[4]).toPath())) {
                String[] p = line.trim().split("\\s+");
                if (p.length < 2 || p[0].startsWith("#")) continue;
                Function f = getFunctionAt(toAddr(Long.parseLong(p[0], 16)));
                if (f == null) continue;
                f.setName(p[1], ghidra.program.model.symbol.SourceType.USER_DEFINED);
                f.setCustomVariableStorage(false);
                f.replaceParameters(Function.FunctionUpdateType.DYNAMIC_STORAGE_ALL_PARAMS, true,
                    ghidra.program.model.symbol.SourceType.USER_DEFINED,
                    new ghidra.program.model.listing.ParameterImpl("fn", ghidra.program.model.data.ShortDataType.dataType, currentProgram));
                f.setReturnType(ghidra.program.model.data.LongDataType.dataType, ghidra.program.model.symbol.SourceType.USER_DEFINED);
                f.setVarArgs(true);
                f.setStackPurgeSize(0);
            }
        }
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        PrintWriter pw = new PrintWriter(new FileWriter(out));
        int n = 0;
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            pw.println("// ==== " + f.getEntryPoint() + " " + f.getName());
            if (r != null && r.decompileCompleted()) pw.println(r.getDecompiledFunction().getC());
            else pw.println("// decompile failed");
            n++;
        }
        pw.close();
        println("decompiled " + n + " functions");
    }
}
