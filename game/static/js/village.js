// Village: live build countdowns. Pure enhancement — the page works without it
// (a reload always re-syncs timers server-side). Each building under construction
// carries data-finish (unix ms); we tick the label and reload when one completes.
(function () {
  var timers = Array.prototype.slice.call(document.querySelectorAll(".vb-timer[data-finish]"));
  if (!timers.length) return;

  function fmt(ms) {
    var s = Math.max(0, Math.round(ms / 1000));
    var m = Math.floor(s / 60);
    s = s % 60;
    return m > 0 ? m + "m " + s + "s" : s + "s";
  }

  function tick() {
    var now = Date.now();
    var doneSomething = false;
    timers.forEach(function (el) {
      var finish = parseInt(el.getAttribute("data-finish"), 10);
      var left = finish - now;
      if (left <= 0) {
        el.textContent = "✅";
        doneSomething = true;
      } else {
        el.textContent = "⏳ " + fmt(left);
      }
    });
    // A build just finished — reload to collect production and unlock upgrades.
    if (doneSomething) setTimeout(function () { location.reload(); }, 600);
  }

  tick();
  setInterval(tick, 1000);
})();
