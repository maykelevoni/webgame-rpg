// Village: tap-a-building option modals + a Build palette modal, plus live build
// countdowns. Actions are plain POST forms (they reload the page, which re-syncs).
(function () {
  var modalRoot = document.getElementById("modal-root");
  var cfg = document.getElementById("vcfg");
  if (!modalRoot || !cfg) return;
  var CSRF = cfg.dataset.csrf;
  var UPGRADE_URL = cfg.dataset.upgradeUrl;
  var BUILD_URL = cfg.dataset.buildUrl;

  function open(html) { modalRoot.innerHTML = html; modalRoot.hidden = false; }
  function close() { modalRoot.hidden = true; modalRoot.innerHTML = ""; }
  function csrf() { return '<input type="hidden" name="csrfmiddlewaretoken" value="' + CSRF + '">'; }
  function cost(w, s) { return "🪵" + w + (s > 0 ? " 🪨" + s : ""); }

  // --- a building's options modal -----------------------------------------
  function buildingModal(d) {
    var body;
    if (d.status === "building") {
      body = "<p>🚧 Under construction…</p>";
    } else {
      body = "<p>Level <b>" + d.level + "</b> / " + d.max + "</p>";
      if (d.produces && +d.rate > 0) body += "<p>Produces <b>+" + d.rate + "</b> " + d.produces + "/min</p>";
      if (d.canUpgrade === "1") {
        body += '<form method="post" action="' + UPGRADE_URL + '">' + csrf() +
          '<input type="hidden" name="building_id" value="' + d.id + '">' +
          '<button type="submit">⬆ Upgrade → Lv ' + (+d.level + 1) +
          " (" + cost(d.upWood, +d.upStone) + ")</button></form>";
      } else {
        body += '<p class="hint">Already at max level.</p>';
      }
    }
    if (d.barracks === "1") body += '<p class="hint">Train soldiers in the Army panel below.</p>';
    open('<div class="modal panel"><div class="modal-head"><h2>' + d.emoji + " " + d.name +
      '</h2><button class="modal-x" data-close>✕</button></div>' + body + "</div>");
  }
  document.querySelectorAll(".vbuild").forEach(function (card) {
    card.addEventListener("click", function () { buildingModal(card.dataset); });
  });

  // --- the Build palette modal --------------------------------------------
  var palEl = document.getElementById("palette-data");
  var palette = palEl ? JSON.parse(palEl.textContent) : [];
  function buildModal() {
    var rows = palette.map(function (b) {
      var locked = b.locked || b.at_limit || !b.affordable;
      var action = locked
        ? '<span class="hint">' + (b.locked ? "🔒 Town Hall Lv " + b.requires_lh
            : (b.at_limit ? "⛔ limit" : "need resources")) + "</span>"
        : '<form method="post" action="' + BUILD_URL + '">' + csrf() +
          '<input type="hidden" name="type_key" value="' + b.key + '"><button type="submit">Build</button></form>';
      return "<tr><td>" + b.name + " <small class='hint'>[" + b.count + "/" + b.max_count + "]</small></td>" +
        "<td>" + cost(b.cost_wood, b.cost_stone) + "</td><td>" + action + "</td></tr>";
    }).join("") || '<tr><td colspan="3" class="hint">Nothing available yet.</td></tr>';
    open('<div class="modal panel"><div class="modal-head"><h2>🔨 Build</h2>' +
      '<button class="modal-x" data-close>✕</button></div><table class="shop-table">' + rows + "</table></div>");
  }
  var bb = document.getElementById("open-build");
  if (bb) bb.addEventListener("click", buildModal);

  // close on ✕ / backdrop / Escape
  modalRoot.addEventListener("click", function (e) {
    if (e.target.dataset.close !== undefined || e.target === modalRoot) close();
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });

  // --- live build countdowns (reload when one finishes) -------------------
  var timers = Array.prototype.slice.call(document.querySelectorAll(".vb-timer[data-finish]"));
  function fmt(ms) { var s = Math.max(0, Math.round(ms / 1000)), m = Math.floor(s / 60); s %= 60; return m > 0 ? m + "m " + s + "s" : s + "s"; }
  function tick() {
    if (!timers.length) return;
    var now = Date.now(), done = false;
    timers.forEach(function (el) {
      var left = parseInt(el.getAttribute("data-finish"), 10) - now;
      if (left <= 0) { el.textContent = "✅"; done = true; } else { el.textContent = "⏳ " + fmt(left); }
    });
    if (done) setTimeout(function () { location.reload(); }, 600);
  }
  tick();
  setInterval(tick, 1000);
})();
