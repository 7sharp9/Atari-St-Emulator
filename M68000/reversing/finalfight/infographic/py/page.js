(function () {
  // hover tips on figures
  var tip = document.getElementById("tip");
  function show(e, el) {
    var t = el.getAttribute("data-tip"); if (!t) return;
    tip.textContent = t; tip.style.display = "block";
    var x = e.clientX + 14, y = e.clientY + 14, w = tip.offsetWidth, h = tip.offsetHeight;
    if (x + w > window.innerWidth - 8) x = e.clientX - w - 14;
    if (y + h > window.innerHeight - 8) y = e.clientY - h - 14;
    tip.style.left = Math.max(8, x) + "px"; tip.style.top = Math.max(8, y) + "px";
  }
  document.querySelectorAll(".cell").forEach(function (el) {
    el.addEventListener("mousemove", function (e) { show(e, el); });
    el.addEventListener("mouseleave", function () { tip.style.display = "none"; });
  });

  // the try-it widget: the same tests the game runs, on boxes read from the ROM
  var D = JSON.parse(document.getElementById("ffdata").textContent);
  var $ = function (id) { return document.getElementById(id); };
  var blowSel = $("w-blow"), victSel = $("w-vict"), xr = $("w-x"), gr = $("w-g"), sp = $("w-special");
  D.blows.forEach(function (b, i) {
    var o = document.createElement("option"); o.value = i; o.textContent = b.label; blowSel.appendChild(o);
  });
  D.victims.forEach(function (v, i) {
    var o = document.createElement("option"); o.value = i; o.textContent = v.label; victSel.appendChild(o);
  });
  function hex(n) { return "$" + (n & 0xffff).toString(16); }
  function passes(d, s) { return ((d + s) & 0xffff) <= ((2 * s) & 0xffff); }
  function el(tag, attrs, text) {
    var s = "<" + tag;
    for (var k in attrs) s += " " + k + '="' + attrs[k] + '"';
    return s + ">" + (text === undefined ? "" : text) + "</" + tag + ">";
  }
  function rect(x0, x1, y0, y1, cls) { return el("rect", { x: x0, y: y0, width: x1 - x0, height: y1 - y0, "class": cls }); }

  function update() {
    var b = D.blows[+blowSel.value], v = D.victims[+victSel.value];
    var X = +xr.value, G = +gr.value, special = sp.checked;
    $("w-xo").textContent = (X >= 0 ? "+" : "") + X; $("w-go").textContent = (G >= 0 ? "+" : "") + G;
    var lo = special ? -24 : -12, hi = special ? 24 : 9;
    var qx = X + 128 >= 0 && X + 128 <= 256, lane = G >= lo && G <= hi;
    var ax = b.dx, ay = b.dy, vcx = X + v.dx, vcy = G + v.dy;
    var sx = b.hw + v.hw, sy = b.hh + v.hh, dx = vcx - ax, dy = vcy - ay;
    var px = passes(dx, sx), py = passes(dy, sy);
    var queued = qx && lane, hit = queued && px && py;

    function gate(id, n, state, v1, d1) {
      var g = $(id); g.className = "gate " + (state === "ok" ? "ok" : state === "no" ? "no" : "");
      g.innerHTML = '<div class="n">' + n + '</div><div class="v">' + (state === "ok" ? "pass" : state === "no" ? "fail" : "not run") + '</div><div class="d">' + d1 + "</div>";
    }
    gate("g-x", "1 Reach list", qx ? "ok" : "no", "", "(x + $80) = " + (X + 128) + ", limit $100 = 256");
    gate("g-l", "2 Depth lane", lane ? "ok" : "no", "", "ground line gap " + G + ", window " + lo + " to +" + hi);
    gate("g-ox", "3 Overlap in x", queued ? (px ? "ok" : "no") : "skip", "", queued ? "dx " + dx + ", s " + sx + ": " + ((dx + sx) & 0xffff) + " vs 2s " + 2 * sx : "never queued");
    gate("g-oy", "4 Overlap in y", queued && px ? (py ? "ok" : "no") : "skip", "", queued && px ? "dy " + dy + ", s " + sy + ": " + ((dy + sy) & 0xffff) + " vs 2s " + 2 * sy : queued ? "only run when x passes" : "never queued");
    var vd = $("w-verdict");
    vd.className = "verdict " + (hit ? "ok" : "no");
    vd.textContent = hit ? "Hit: the blow lands" : !qx ? "Miss: victim is not in the reach list" : !lane ? "Miss: victim is outside the depth lane" : !px ? "Miss: boxes do not meet in x" : "Miss: boxes do not meet in height";

    // side view: x across, height above the player's feet up
    var X0 = -190, W = 380, H0 = 112, Hh = 126;
    function SX(x) { return x - X0; } function SY(h) { return H0 - h; }
    var s = "";
    for (var t = -160; t <= 160; t += 32) s += el("line", { x1: SX(t), y1: SY(0), x2: SX(t), y2: SY(0) + 3, stroke: "currentColor", "class": "tick" }) + el("text", { x: SX(t), y: SY(0) + 12, "text-anchor": "middle" }, t);
    s += el("line", { x1: 0, y1: SY(0), x2: W, y2: SY(0), "class": "ground" });
    s += rect(SX(-128), SX(128), SY(0) - 2, SY(0) + 2, "win");
    s += rect(SX(-14), SX(14), SY(71), SY(-1), "bx hurt dim");
    s += rect(SX(vcx - v.hw), SX(vcx + v.hw), SY(vcy + v.hh), SY(vcy - v.hh), "bx hurt");
    s += el("line", { x1: SX(X + v.dx - v.hw - 4), y1: SY(G), x2: SX(X + v.dx + v.hw + 4), y2: SY(G), "class": "ground", "stroke-dasharray": "2 2" });
    s += rect(SX(ax - b.hw), SX(ax + b.hw), SY(ay + b.hh), SY(ay - b.hh), "bx " + (hit ? "hit" : "atk"));
    if (hit) s += rect(SX(vcx - v.hw), SX(vcx + v.hw), SY(vcy + v.hh), SY(vcy - v.hh), "bx hit");
    s += el("text", { x: SX(-14), y: SY(71) - 4, "text-anchor": "middle" }, "you");
    s += el("text", { x: SX(vcx), y: SY(Math.max(vcy + v.hh, ay + b.hh)) - 6, "text-anchor": "middle" }, "victim");
    $("w-side").innerHTML = s;

    // top view: x across, depth up (further back is up, as on the screen)
    var T0 = 34, TH = 70;
    function TY(d) { return T0 - d; }
    var t2 = rect(SX(-128), SX(128), TY(hi), TY(lo), "win");
    t2 += el("line", { x1: 0, y1: TY(0), x2: W, y2: TY(0), "class": "ground", "stroke-dasharray": "1 3" });
    t2 += el("circle", { cx: SX(0), cy: TY(0), r: 3.5, fill: "var(--hurt)" }) + el("text", { x: SX(0) + 7, y: TY(0) + 3 }, "you");
    t2 += el("circle", { cx: SX(X), cy: TY(G), r: 3.5, fill: hit ? "var(--hit)" : "var(--atk)" }) + el("text", { x: SX(X) + 7, y: TY(G) - 5 }, "victim " + (G >= 0 ? "+" : "") + G);
    t2 += el("text", { x: 4, y: 9 }, "further back");
    t2 += el("text", { x: 4, y: TH - 3 }, "closer to the camera");
    $("w-top").innerHTML = t2;
  }
  [blowSel, victSel, xr, gr, sp].forEach(function (c) { c.addEventListener("input", update); c.addEventListener("change", update); });
  document.querySelectorAll("button.pre").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var p = JSON.parse(btn.getAttribute("data-p"));
      blowSel.value = p.blow; victSel.value = p.vict; xr.value = p.x; gr.value = p.g; sp.checked = !!p.sp; update();
    });
  });
  var first = document.querySelector("button.pre");
  if (first) first.click(); else update();
})();
