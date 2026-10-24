// Health Dashboard - inlined by scripts/build_dashboard.py.
// Obsidian reloads the file after every rebuild: keep the chosen tab and
// pickers in localStorage. Tooltips for every element with data-tip
// ("when|value").
(function () {
  var TAB_KEY = "health-dashboard-tab";

  function load(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }

  function save(key, value) {
    try { localStorage.setItem(key, value); } catch (e) {}
  }

  var saved = load(TAB_KEY);
  var savedTab = saved && document.getElementById(saved);
  if (savedTab) savedTab.checked = true;
  document.querySelectorAll(".tab-input").forEach(function (input) {
    input.addEventListener("change", function () { save(TAB_KEY, input.id); });
  });

  // Pickers (e1RM, session comparison): show one panel, remember the choice.
  document.querySelectorAll("select.picker").forEach(function (sel) {
    var group = sel.getAttribute("data-group");
    var key = "health-dashboard-" + group;
    var panels = document.querySelectorAll('[data-panel="' + group + '"]');
    function show() {
      panels.forEach(function (p) { p.hidden = p.id !== sel.value; });
    }
    var savedPanel = load(key);
    if (savedPanel && document.getElementById(savedPanel)) sel.value = savedPanel;
    sel.addEventListener("change", function () {
      show();
      save(key, sel.value);
    });
    show();
  });

  var tip = document.createElement("div");
  tip.className = "tip";
  tip.setAttribute("role", "tooltip");
  var tipWhen = document.createElement("span");
  tipWhen.className = "tip-when";
  var tipValue = document.createElement("b");
  tip.appendChild(tipWhen);
  tip.appendChild(tipValue);
  document.body.appendChild(tip);
  var current = null;

  function place(x, y) {
    var r = tip.getBoundingClientRect();
    var left = Math.min(Math.max(8, x - r.width / 2), window.innerWidth - r.width - 8);
    var top = y - r.height - 14;
    if (top < 8) top = y + 18;
    tip.style.transform = "translate(" + Math.round(left) + "px," + Math.round(top) + "px)";
  }

  function show(el, x, y) {
    if (el !== current) {
      current = el;
      var parts = (el.getAttribute("data-tip") || "").split("|");
      tipWhen.textContent = parts[0] || "";
      tipValue.textContent = parts.slice(1).join("|");
    }
    place(x, y);
    tip.classList.add("on");
  }

  function hide() {
    current = null;
    tip.classList.remove("on");
  }

  function onPointer(e) {
    var el = e.target && e.target.closest ? e.target.closest("[data-tip]") : null;
    if (el) show(el, e.clientX, e.clientY);
    else if (current) hide();
  }

  document.addEventListener("pointermove", onPointer);
  document.addEventListener("pointerdown", onPointer);
  document.documentElement.addEventListener("pointerleave", hide);
  window.addEventListener("scroll", hide, { passive: true });
})();
