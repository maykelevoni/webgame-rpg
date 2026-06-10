// explore.js — smooth, no-reload exploration + on-map service modals.
//
// Movement and shop/rest actions go to the same server endpoints as the no-JS
// fallback, but via fetch: we repaint just the grid (no full-page flash, so monster
// steps read smoothly) and open the market/hospital as modals on the map.
(function () {
  const grid = document.getElementById("map-grid");
  if (!grid) return;
  const cfg = grid.dataset;
  const modalRoot = document.getElementById("modal-root");

  // --- server calls --------------------------------------------------------
  function post(url, data) {
    const body = new URLSearchParams(data || {});
    return fetch(url, {
      method: "POST",
      headers: { "X-Requested-With": "fetch", "X-CSRFToken": cfg.csrf,
                 "Content-Type": "application/x-www-form-urlencoded" },
      body,
    }).then((r) => r.json());
  }
  function getJSON(url) {
    return fetch(url, { headers: { "X-Requested-With": "fetch" } }).then((r) => r.json());
  }

  // --- rendering -----------------------------------------------------------
  function cellHTML(cell) {
    const cls = "cell terrain-" + cell.terrain + (cell.is_player ? " player" : "");
    let inner = "";
    if (cell.sprite) {
      inner = `<img class="spr" src="${cfg.spriteBase}${cell.sprite}.png" alt="">`;
    } else if (cell.emoji) {
      inner = `<span class="map-emoji">${cell.emoji}</span>`;
    }
    const title = (cell.label || "").replace(/"/g, "");
    return `<div class="${cls}" title="${title}">${inner}</div>`;
  }
  function repaint(data) {
    grid.style.gridTemplateColumns = `repeat(${data.size}, 1fr)`;
    if (data.biome) {
      grid.className = grid.className.replace(/\bbiome-\S+/g, "").trim() + " biome-" + data.biome;
    }
    grid.innerHTML = data.grid.map((row) => row.map(cellHTML).join("")).join("");
  }
  function updateHud(data) {
    if (data.gold != null) setText("hud-gold", data.gold);
    if (data.hp != null) {
      setText("hud-hp", data.hp);
      setText("hud-maxhp", data.max_hp);
      const bar = document.getElementById("hud-hp-bar");
      if (bar) bar.style.width = Math.round((data.hp / data.max_hp) * 100) + "%";
    }
    if (data.area) setText("hud-area", "📍 " + data.area);
  }
  function setText(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }

  // --- transient toast -----------------------------------------------------
  function toast(msg) {
    if (!msg) return;
    let t = document.getElementById("toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "toast";
      t.className = "toast";
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove("show"), 1800);
  }

  // --- movement ------------------------------------------------------------
  let busy = false;
  function move(direction) {
    if (busy || !modalRoot.hidden) return;     // ignore while a modal is open
    if (document.getElementById("battle-overlay")) return;   // can't walk mid-fight
    busy = true;
    post(cfg.moveUrl, { direction }).then((data) => {
      busy = false;
      if (data.combat) { window.location.reload(); return; }   // into the combat overlay
      if (data.recovering) { toast(data.message); return; }    // hero laid up after a raid
      if (data.building) { useBuilding(data.building); return; }  // bumped a settlement building
      repaint(data);
      updateHud(data);
      if (data.minigame === "resource") openStrikeGame("resource", data.resource);
      else if (data.minigame === "chest") openStrikeGame("chest");
    }).catch(() => { busy = false; });
  }

  // d-pad buttons call move() instead of submitting (which reloaded the page).
  document.querySelectorAll(".dpad form").forEach((form) => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const dir = form.querySelector("[name=direction]").value;
      move(dir);
    });
  });
  // arrow / WASD keys
  const KEYS = { ArrowUp: "north", ArrowDown: "south", ArrowLeft: "west", ArrowRight: "east",
                 w: "north", s: "south", a: "west", d: "east" };
  document.addEventListener("keydown", (e) => {
    const dir = KEYS[e.key];
    if (dir) { e.preventDefault(); move(dir); }
  });

  // Bumping a castle station uses it: market -> shop modal, mead hall -> rest,
  // smithy/vault -> their panels, "village" -> the road to your build screen.
  function useBuilding(key) {
    if (key === "market") return openMarket();
    if (key === "hospital") {
      return post(cfg.restUrl, {}).then((s) => { toast(s.message); updateHud(s); });
    }
    if (key === "village" || key === "longhouse") { window.location = cfg.villageUrl; return; }
    if (key === "smithy") return openSmithy();
    if (key === "vault") return openVault();
    openMarket();   // unknown station: fall back to the market modal
  }

  function infoModal(title, body) {
    modalRoot.innerHTML = `
      <div class="modal panel">
        <div class="modal-head"><h2>${title}</h2><button class="modal-x" data-close>✕</button></div>
        <p>${body}</p>
      </div>`;
    modalRoot.hidden = false;
  }

  // --- combat in place (bars/log update; monster & player shake when hit) --
  let lastMonHp = null, lastPlHp = null;
  function shake(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("hit"); void el.offsetWidth; el.classList.add("hit");
  }
  function setBar(id, hp, max) {
    const bar = document.getElementById(id);
    if (bar) bar.style.width = Math.max(0, Math.round((hp / max) * 100)) + "%";
  }
  // Float a damage (red) or heal (green) number up from a combatant sprite.
  function floatNum(spriteId, amount, kind) {
    const el = document.getElementById(spriteId);
    if (!el || !amount) return;
    const f = document.createElement("span");
    f.className = "dmg-float " + (kind || "dmg");
    f.textContent = (kind === "heal" ? "+" : "-") + Math.abs(amount);
    (el.parentElement || el).appendChild(f);
    setTimeout(() => f.remove(), 850);
  }
  function combatAction(data) {
    post(cfg.combatUrl, data).then((d) => {
      if (d.error) return;
      const monDmg = lastMonHp != null ? lastMonHp - d.monster_hp : 0;
      const plDelta = lastPlHp != null ? lastPlHp - d.player_hp : 0;
      if (monDmg > 0) { shake("battle-monster"); floatNum("battle-monster", monDmg, "dmg"); }
      if (plDelta > 0) { shake("battle-player"); floatNum("battle-player", plDelta, "dmg"); }
      else if (plDelta < 0) floatNum("battle-player", plDelta, "heal");   // healed by an item
      lastMonHp = d.monster_hp; lastPlHp = d.player_hp;
      setBar("mon-hp-bar", d.monster_hp, d.monster_max);
      setText("mon-hp-text", `${d.monster_hp} / ${d.monster_max}`);
      setBar("pl-hp-bar", d.player_hp, d.player_max);
      setText("pl-hp-text", `${d.player_hp} / ${d.player_max}`);
      const log = document.getElementById("battle-log");
      if (log) { log.innerHTML = d.log.map((l) => `<div>${l}</div>`).join(""); log.scrollTop = log.scrollHeight; }
      if (d.outcome !== "ongoing") showCombatResult(d);
    });
  }
  function showCombatResult(d) {
    const overlay = document.getElementById("battle-overlay");
    if (overlay) overlay.style.display = "none";    // clear the battle screen first
    const title = d.outcome === "win" ? "⚔️ Victory!" :
      d.outcome === "lose" ? "💀 Defeated…" : "🏃 You fled";
    const body = d.outcome === "win"
      ? `<p>You defeated the ${d.monster}.</p><div class="strike-stage"><span class="strike-result">+${d.gold} 🪙 · +${d.xp} XP</span></div>`
      : d.outcome === "lose"
      ? `<div class="strike-stage"><span class="strike-result">You wake at the start — half your gold lost.</span></div>`
      : `<div class="strike-stage"><span class="strike-result">You slipped away.</span></div>`;
    modalRoot.innerHTML = `
      <div class="modal panel minigame">
        <div class="modal-head"><h2>${title}</h2></div>${body}
        <div class="modal-actions"><button id="combat-continue">▶ Continue</button></div>
      </div>`;
    modalRoot.hidden = false;
    document.getElementById("combat-continue").addEventListener("click", () => window.location.reload());
  }
  (function bindCombat() {
    const overlay = document.getElementById("battle-overlay");
    if (!overlay) return;
    const mt = document.getElementById("mon-hp-text");
    const pt = document.getElementById("pl-hp-text");
    if (mt) lastMonHp = parseInt(mt.textContent, 10);
    if (pt) lastPlHp = parseInt(pt.textContent, 10);
    overlay.querySelectorAll(".battle-actions form").forEach((form) => {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        const data = {};
        form.querySelectorAll("[name]").forEach((i) => {
          if (i.name !== "csrfmiddlewaretoken") data[i.name] = i.value;
        });
        combatAction(data);
      });
    });
  })();

  // --- market / hospital modal --------------------------------------------
  function closeModal() { modalRoot.hidden = true; modalRoot.innerHTML = ""; }

  function openMarket() {
    getJSON(cfg.shopUrl).then(renderMarket);
  }
  function renderMarket(s) {
    const buyRows = s.items.map((i) => `
      <tr><td>${i.name}</td><td>🪙 ${i.price}</td>
      <td><button data-buy="${i.key}" ${s.gold < i.price ? "disabled" : ""}>Buy</button></td></tr>`).join("");
    const sellRows = s.inventory.filter((i) => i.sellable).map((i) => `
      <tr><td>${i.name} ×${i.quantity}</td><td>🪙 ${Math.floor(i.price / 2)}</td>
      <td><button data-sell="${i.key}">Sell</button></td></tr>`).join("") ||
      `<tr><td colspan="3" class="hint">Nothing to sell.</td></tr>`;
    const RES = { wood: "🪵", stone: "🪨", meat: "🍖", iron: "⛏️" };
    const r = s.resources || {}, rates = s.sell_rates || {};
    const resRows = Object.keys(RES).map((k) => `
      <tr><td>${RES[k]} ${k} ×${r[k] || 0}</td><td>🪙 ${rates[k] || 0}/ea</td>
      <td><button data-sellres="${k}" data-amt="10" ${(r[k] || 0) < 10 ? "disabled" : ""}>Sell 10</button>
          <button data-sellres="${k}" data-amt="all" ${(r[k] || 0) <= 0 ? "disabled" : ""}>All</button></td></tr>`).join("");
    modalRoot.innerHTML = `
      <div class="modal panel">
        <div class="modal-head">
          <h2>🏪 The Market</h2>
          <button class="modal-x" data-close>✕</button>
        </div>
        <p>🪙 <b id="m-gold">${s.gold}</b> gold</p>
        <div class="shop-cols">
          <div><h3>Buy</h3><table class="shop-table">${buyRows}</table></div>
          <div><h3>Sell items</h3><table class="shop-table">${sellRows}</table></div>
        </div>
        <h3>Sell village surplus</h3>
        <table class="shop-table">${resRows}</table>
      </div>`;
    modalRoot.hidden = false;
  }

  // --- castle smithy (refine gear with iron + gold) ------------------------
  function openSmithy() { getJSON(cfg.smithyUrl).then(renderSmithy); }
  function renderSmithy(s) {
    const rows = (s.gear || []).map((g) => {
      const tag = g.boost === "atk" ? "⚔️" : "🛡️";
      const lvl = g.level ? ` <b>+${g.level}</b>` : "";
      const action = g.at_max
        ? `<span class="hint">max +${s.max_level}</span>`
        : `<button data-refine="${g.id}" ${(s.iron < g.next_iron || s.gold < g.next_gold) ? "disabled" : ""}>`
          + `Refine → +${g.level + 1} (⛏️${g.next_iron} 🪙${g.next_gold}, ${g.next_chance}%)</button>`;
      return `<tr><td>${tag} ${g.name}${lvl}${g.equipped ? " <i class='hint'>(worn)</i>" : ""}</td>
              <td>${action}</td></tr>`;
    }).join("") || `<tr><td colspan="2" class="hint">No weapons or armour to refine.</td></tr>`;
    modalRoot.innerHTML = `
      <div class="modal panel">
        <div class="modal-head"><h2>🔨 The Smithy</h2><button class="modal-x" data-close>✕</button></div>
        <p>⛏️ <b id="sm-iron">${s.iron}</b> iron &nbsp;·&nbsp; 🪙 <b id="sm-gold">${s.gold}</b> gold</p>
        <p class="hint">Refines up to +${s.safe_level} always succeed. Above that, a failure drops the gear a level.</p>
        <table class="shop-table">${rows}</table>
        <p id="sm-result" class="strike-result" style="min-height:1.2em;"></p>
      </div>`;
    modalRoot.hidden = false;
  }
  function doRefine(invId) {
    post(cfg.refineUrl, { inv_id: invId }).then((d) => {
      if (d.error) { toast(d.error); return; }
      renderSmithy(d);
      updateHud(d);
      const res = document.getElementById("sm-result");
      if (res) res.textContent = (d.success ? "✅ " : "💥 ") + d.message;
      toast(d.message);
    });
  }

  // --- castle vault (stash gold, safe from the death penalty) --------------
  function openVault() { getJSON(cfg.vaultUrl).then(renderVault); }
  function renderVault(s) {
    modalRoot.innerHTML = `
      <div class="modal panel">
        <div class="modal-head"><h2>💰 The Vault</h2><button class="modal-x" data-close>✕</button></div>
        <p class="hint">Gold in the Vault is safe — death only takes <b>carried</b> gold.</p>
        <p>👜 Carried <b id="vault-carried">${s.gold}</b> 🪙 &nbsp;·&nbsp; 💰 Stashed <b id="vault-stashed">${s.vault_gold}</b> 🪙</p>
        <div class="vault-cols">
          <div>
            <h3>Deposit</h3>
            <input type="number" id="vault-dep-amt" min="1" placeholder="amount" class="vault-input">
            <div class="modal-actions">
              <button data-vault="deposit" data-input="vault-dep-amt" ${s.gold <= 0 ? "disabled" : ""}>Deposit</button>
              <button data-vault="deposit" data-amt="all" ${s.gold <= 0 ? "disabled" : ""}>All</button>
            </div>
          </div>
          <div>
            <h3>Withdraw</h3>
            <input type="number" id="vault-wd-amt" min="1" placeholder="amount" class="vault-input">
            <div class="modal-actions">
              <button data-vault="withdraw" data-input="vault-wd-amt" ${s.vault_gold <= 0 ? "disabled" : ""}>Withdraw</button>
              <button data-vault="withdraw" data-amt="all" ${s.vault_gold <= 0 ? "disabled" : ""}>All</button>
            </div>
          </div>
        </div>
      </div>`;
    modalRoot.hidden = false;
  }
  function doVault(action, amount) {
    post(cfg.vaultMoveUrl, { action, amount }).then((d) => {
      if (d.error) { toast(d.error); return; }
      renderVault(d); updateHud(d); toast(d.message);
    });
  }

  // --- inventory / equipment (paper-doll) ----------------------------------
  function openInventory() { getJSON(cfg.invUrl).then(renderInventory); }
  function renderInventory(s) {
    const slots = (s.slots || []).map((sl) => {
      const it = sl.item;
      const body = it
        ? `<b>${it.name}${it.refine ? " +" + it.refine : ""}</b>
           <small>${it.atk ? " +" + (it.atk + (it.refine || 0)) + "⚔️" : ""}${it.def ? " +" + (it.def + (it.refine || 0)) + "🛡️" : ""}</small>
           <button data-unequip="${sl.slot}">Unequip</button>`
        : `<span class="hint">empty</span>`;
      return `<div class="doll-slot"><div class="doll-emoji">${sl.emoji}</div>
              <div class="doll-label">${sl.label}</div>${body}</div>`;
    }).join("");
    const rows = (s.inventory || []).filter((i) => !i.equipped).map((i) => {
      const action = i.slot ? `<button data-equip="${i.key}">Equip</button>`
        : (i.kind === "consumable" ? `<button data-use="${i.key}">Use</button>` : "");
      const plus = i.slot && i.refine ? `+${i.refine} ` : "";
      return `<tr><td>${plus}${i.name} ×${i.quantity}</td><td>${action}</td></tr>`;
    }).join("") || `<tr><td colspan="2" class="hint">Your pack is empty.</td></tr>`;
    modalRoot.innerHTML = `
      <div class="modal panel">
        <div class="modal-head"><h2>🎒 Inventory</h2><button class="modal-x" data-close>✕</button></div>
        <p>⚔️ atk <b>${s.eff_atk}</b> &nbsp; 🛡️ def <b>${s.eff_def}</b> &nbsp; 🪙 ${s.gold} &nbsp; ❤️ ${s.hp}/${s.max_hp}</p>
        <div class="doll-grid">${slots}</div>
        <h3>Pack</h3>
        <table class="shop-table">${rows}</table>
      </div>`;
    modalRoot.hidden = false;
  }
  function refreshInv(promise) {
    promise.then((s) => {
      if (s.error) { toast(s.error); return; }
      toast(s.message); renderInventory(s); updateHud(s);
    });
  }
  const invBtn = document.getElementById("open-inventory");
  if (invBtn) invBtn.addEventListener("click", openInventory);
  document.addEventListener("keydown", (e) => {
    if ((e.key === "i" || e.key === "I") && modalRoot.hidden &&
        !document.getElementById("battle-overlay")) {
      e.preventDefault(); openInventory();
    }
  });

  // delegate clicks inside the modal
  modalRoot.addEventListener("click", (e) => {
    const t = e.target;
    if (t.dataset.close !== undefined || t === modalRoot) return closeModal();
    if (t.dataset.buy) refresh(post(cfg.buyUrl, { item_key: t.dataset.buy }));
    else if (t.dataset.sell) refresh(post(cfg.sellUrl, { item_key: t.dataset.sell }));
    else if (t.dataset.sellres) refresh(post(cfg.sellResUrl, { resource: t.dataset.sellres, amount: t.dataset.amt }));
    else if (t.dataset.rest !== undefined) refresh(post(cfg.restUrl, {}));
    else if (t.dataset.refine) doRefine(t.dataset.refine);
    else if (t.dataset.vault) {
      const amt = t.dataset.amt || (t.dataset.input && document.getElementById(t.dataset.input).value);
      doVault(t.dataset.vault, amt || "0");
    }
    else if (t.dataset.equip) refreshInv(post(cfg.equipUrl, { item_key: t.dataset.equip }));
    else if (t.dataset.unequip) refreshInv(post(cfg.unequipUrl, { slot: t.dataset.unequip }));
    else if (t.dataset.use) refreshInv(post(cfg.useUrl, { item_key: t.dataset.use }));
  });
  modalRoot.addEventListener("click", (e) => { if (e.target === modalRoot) closeModal(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

  function refresh(promise) {
    promise.then((s) => {
      if (s.error) { toast(s.error); return; }
      toast(s.message); renderMarket(s); updateHud(s);
    });
  }

  // --- resource / chest strike animation -----------------------------------
  // No skill check: you click to strike, the node shakes & cracks, and after a few
  // hits it shatters and you collect. Tool/upgrades can tune the hit count later.
  const RES_EMOJI = { wood: "🪵", stone: "🪨", meat: "🍖" };
  function openStrikeGame(kind, resource) {
    const isChest = kind === "chest";
    const icon = isChest ? "📦" : (RES_EMOJI[resource] || "🪨");
    const hitsNeeded = isChest ? 2 : (resource === "stone" ? 5 : 4);  // rock is tougher
    const verb = isChest ? "Open" : "Strike";
    modalRoot.innerHTML = `
      <div class="modal panel minigame">
        <div class="modal-head"><h2>${isChest ? "Cracking the chest" : "Harvesting " + resource}</h2></div>
        <div class="strike-stage"><span class="strike-node" id="snode">${icon}</span></div>
        <div class="integ-bar"><span class="integ-fill" id="integ" style="width:100%"></span></div>
        <div class="modal-actions"><button id="strike-btn">💥 ${verb}</button></div>
      </div>`;
    modalRoot.hidden = false;

    const node = document.getElementById("snode");
    const integ = document.getElementById("integ");
    const btn = document.getElementById("strike-btn");
    let hits = 0, done = false;

    btn.addEventListener("click", () => {
      if (done) return;
      hits += 1;
      // replay the shake animation + spit out a chip
      node.classList.remove("hit"); void node.offsetWidth; node.classList.add("hit");
      const chip = document.createElement("span");
      chip.className = "chip"; chip.textContent = "✦";
      node.parentElement.appendChild(chip);
      setTimeout(() => chip.remove(), 420);
      integ.style.width = Math.max(0, (1 - hits / hitsNeeded) * 100) + "%";

      if (hits >= hitsNeeded) {
        done = true;
        node.classList.add("shatter");
        btn.disabled = true;
        const url = isChest ? cfg.chestUrl : cfg.harvestUrl;
        setTimeout(() => {
          post(url, {}).then((d) => {
            const reward = d.amount != null
              ? `+${d.amount} ${RES_EMOJI[d.resource] || ""} ${d.resource}`
              : d.gold_gain != null ? `+${d.gold_gain} 🪙 gold` : "Collected!";
            modalRoot.querySelector(".minigame").innerHTML = `
              <div class="modal-head"><h2>${isChest ? "Chest opened!" : "Harvested!"}</h2></div>
              <div class="strike-stage"><span class="strike-result">${reward}</span></div>
              <div class="modal-actions"><button id="collect-btn">✔ Collect</button></div>`;
            const finish = () => { closeModal(); if (d.grid) repaint(d); updateHud(d); };
            document.getElementById("collect-btn").addEventListener("click", finish);
          });
        }, 340);
      }
    });
  }
})();
