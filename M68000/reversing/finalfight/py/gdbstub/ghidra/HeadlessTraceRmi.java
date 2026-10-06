// Headless TraceRmi acceptor: builds a GhidraTool inside analyzeHeadless, adds the TraceRmi plugin, accepts one gdb, reads the trace.
import java.net.InetSocketAddress;
import java.util.Collection;

import ghidra.app.plugin.core.debug.service.target.DebuggerTargetServicePlugin;
import ghidra.app.plugin.core.debug.service.tracermi.TraceRmiPlugin;
import ghidra.app.script.GhidraScript;
import ghidra.app.services.TraceRmiService;
import ghidra.debug.api.target.Target;
import ghidra.debug.api.tracermi.*;
import ghidra.framework.plugintool.PluginTool;
import ghidra.framework.project.tool.GhidraTool;
import ghidra.program.model.address.*;
import ghidra.program.model.lang.Register;
import ghidra.trace.model.Trace;
import ghidra.trace.model.memory.*;
import ghidra.trace.model.thread.TraceThread;

public class HeadlessTraceRmi extends GhidraScript {
	@Override
	protected void run() throws Exception {
		int port = Integer.parseInt(System.getProperty("rmi.port", System.getenv().getOrDefault("RMI_PORT", "15433")));
		int waitMs = Integer.parseInt(System.getenv().getOrDefault("RMI_WAIT_MS", "60000"));
		println("project=" + state.getProject() + " tool=" + state.getTool());
		final PluginTool[] holder = new PluginTool[1];
		final Throwable[] err = new Throwable[1];
		javax.swing.SwingUtilities.invokeAndWait(() -> {
			try {
				PluginTool t = new GhidraTool(state.getProject(), "HeadlessDebug");
				t.addPlugin(DebuggerTargetServicePlugin.class.getName());
				t.addPlugin(ghidra.app.plugin.core.debug.service.tracemgr.DebuggerTraceManagerServicePlugin.class.getName());
				t.addPlugin(TraceRmiPlugin.class.getName());
				holder[0] = t;
			}
			catch (Throwable e) { err[0] = e; }
		});
		if (err[0] != null) throw new RuntimeException(err[0]);
		PluginTool tool = holder[0];
		TraceRmiService service = tool.getService(TraceRmiService.class);
		println("service=" + service);
		TraceRmiAcceptor acceptor = service.acceptOne(new InetSocketAddress("127.0.0.1", port));
		println("Listening at " + acceptor.getAddress());
		acceptor.setTimeout(waitMs);
		TraceRmiConnection conn = acceptor.accept();
		println("Connection from " + conn.getRemoteAddress() + " desc=" + conn.getDescription());
		println("methods=" + conn.getMethods());
		Trace trace = conn.waitForTrace(waitMs);
		println("trace=" + trace + " lang=" + trace.getBaseLanguage().getLanguageID());
		// let gdb finish its putreg/putmem script
		long snap = -1;
		long t0 = System.currentTimeMillis();
		while (System.currentTimeMillis() - t0 < waitMs) {
			try { snap = conn.getLastSnapshot(trace); break; }
			catch (java.util.NoSuchElementException e) { Thread.sleep(300); }
		}
		Thread.sleep(Long.parseLong(System.getenv().getOrDefault("RMI_SETTLE_MS", "8000")));
		snap = conn.getLastSnapshot(trace);
		println("snap=" + snap);
		Collection<? extends TraceThread> threads = trace.getThreadManager().getAllThreads();
		println("threads=" + threads);
		for (TraceThread th : threads) {
			TraceMemorySpace rs = trace.getMemoryManager().getMemoryRegisterSpace(th, 0, false);
			println("regspace for " + th + " = " + rs);
			if (rs == null) continue;
			for (String r : new String[] { "D0", "A5", "A7", "SP", "SR", "PC" }) {
				Register reg = trace.getBaseLanguage().getRegister(r);
				if (reg == null) { println("  " + r + " no such register"); continue; }
				try {
					println("  " + r + " = " + rs.getValue(snap, reg));
				}
				catch (Exception e) { println("  " + r + " err " + e); }
			}
		}
		AddressSpace ram = trace.getBaseAddressFactory().getDefaultAddressSpace();
		println("default space=" + ram);
		TraceMemorySpace ms = trace.getMemoryManager().getMemorySpace(ram, false);
		println("memspace=" + ms);
		for (long a : new long[] { 0xff8000L, 0xff0000L, 0xff0ff0L, 0x53eL }) {
			byte[] buf = new byte[16];
			int n = trace.getMemoryManager().getViewBytes(snap, ram.getAddress(a), java.nio.ByteBuffer.wrap(buf));
			StringBuilder sb = new StringBuilder();
			for (int i = 0; i < n; i++) sb.append(String.format("%02x", buf[i]));
			println(String.format("  mem[%x] n=%d %s", a, n, sb));
		}
		// optional: dump the whole 64K work RAM to a file for comparison
		String out = System.getenv("RMI_RAM_OUT");
		if (out != null) {
			byte[] buf = new byte[0x10000];
			int n = trace.getMemoryManager().getViewBytes(snap, ram.getAddress(0xff0000L), java.nio.ByteBuffer.wrap(buf));
			java.nio.file.Files.write(java.nio.file.Path.of(out), buf);
			println("wrote " + out + " bytes read=" + n);
		}
		println("registers/regions: " + trace.getMemoryManager().getAllRegions());
		conn.close();
	}
}
