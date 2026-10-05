(function () {
  var tip = document.getElementById("tip");
  function show(e, el) {
    var t = el.getAttribute("data-tip"); if (!t) return;
    tip.textContent = t; tip.style.display = "block";
    var x = e.clientX + 14, y = e.clientY + 14;
    var w = tip.offsetWidth, h = tip.offsetHeight;
    if (x + w > window.innerWidth - 8) x = e.clientX - w - 14;
    if (y + h > window.innerHeight - 8) y = e.clientY - h - 14;
    tip.style.left = Math.max(8, x) + "px"; tip.style.top = Math.max(8, y) + "px";
  }
  document.querySelectorAll(".cell").forEach(function (el) {
    el.addEventListener("mousemove", function (e) { show(e, el); });
    el.addEventListener("mouseleave", function () { tip.style.display = "none"; });
  });
})();
