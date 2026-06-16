const VIEWS = [
  { key: "total", label: "Total" },
  { key: "average", label: "Average" },
  { key: "per90", label: "Per-90" },
  { key: "bestXI", label: "Best XI" },
];

let DATA = null;
let currentLeague = "all";
let currentView = "total";

// Safe element builder. Text is set via textContent, never innerHTML.
function el(tag, opts = {}) {
  const node = document.createElement(tag);
  if (opts.className) node.className = opts.className;
  if (opts.text != null) node.textContent = opts.text;
  if (opts.attrs) {
    for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
  }
  (opts.children || []).forEach(c => c && node.appendChild(c));
  return node;
}

// <img> that removes itself if the URL is missing or fails to load.
function logoImg(src, cls, alt) {
  if (!src) return null;
  const im = document.createElement("img");
  im.className = cls;
  im.alt = alt || "";
  im.title = alt || "";
  im.loading = "lazy";
  im.onerror = () => im.remove();
  im.src = src;
  return im;
}

// Player avatar: headshot -> national flag -> initials.
function avatar(player) {
  const wrap = el("span", { className: "avatar" });
  const initials = (player.name || "?")
    .split(" ").filter(Boolean).map(s => s[0]).slice(0, 2).join("").toUpperCase();
  const showInitials = () =>
    wrap.replaceChildren(el("span", { className: "initials", text: initials || "?" }));
  const showFlag = () => {
    if (!player.nationFlag) return showInitials();
    const f = document.createElement("img");
    f.className = "ava-img"; f.loading = "lazy"; f.alt = player.nation || "";
    f.onerror = showInitials; f.src = player.nationFlag;
    wrap.replaceChildren(f);
  };
  if (player.headshot) {
    const h = document.createElement("img");
    h.className = "ava-img"; h.loading = "lazy"; h.alt = player.name || "";
    h.onerror = showFlag; h.src = player.headshot;
    wrap.appendChild(h);
  } else {
    showFlag();
  }
  return wrap;
}

function leagueLogoMap() {
  const map = new Map();
  DATA.clubs.forEach(c => { if (c.leagueLogo) map.set(c.league, c.leagueLogo); });
  return map;
}

async function load() {
  const res = await fetch("standings.json", { cache: "no-store" });
  DATA = await res.json();
  buildLeagueTabs();
  buildViewTabs();
  setupExplainer();
  render();
  const when = new Date(DATA.generatedAt).toLocaleString();
  document.getElementById("meta").textContent =
    `Updated ${when} · ${DATA.coverage.playersMapped} players · season ${DATA.season}`;
}

function leagues() {
  const map = new Map();
  DATA.clubs.forEach(c => map.set(c.league, c.leagueName));
  return [["all", "All leagues"], ...map.entries()];
}

function buildLeagueTabs() {
  const wrap = document.getElementById("leagues");
  const logos = leagueLogoMap();
  wrap.replaceChildren(...leagues().map(([key, name]) => {
    const logo = key === "all" ? null : logoImg(logos.get(key), "tab-logo", name);
    const b = el("button", {
      className: key === currentLeague ? "active" : "",
      children: [logo, el("span", { text: name })],
    });
    b.onclick = () => { currentLeague = key; buildLeagueTabs(); render(); };
    return b;
  }));
}

function buildViewTabs() {
  const wrap = document.getElementById("views");
  wrap.replaceChildren(...VIEWS.map(v => {
    const b = el("button", { text: v.label, className: v.key === currentView ? "active" : "" });
    b.onclick = () => { currentView = v.key; buildViewTabs(); render(); };
    return b;
  }));
}

function render() {
  document.getElementById("score-head").textContent =
    VIEWS.find(v => v.key === currentView).label;
  const rows = document.getElementById("rows");
  const logos = leagueLogoMap();

  const clubs = DATA.clubs
    .filter(c => currentLeague === "all" || c.league === currentLeague)
    .slice()
    .sort((a, b) => b.scores[currentView] - a.scores[currentView]);

  const nodes = [];
  clubs.forEach((c, i) => {
    const clubCell = el("td", { className: "club-cell", children: [
      logoImg(c.clubLogo, "crest", c.club),
      el("span", { text: c.club }),
    ]});
    const leagueCell = el("td", { className: "league-cell", children: [
      logoImg(logos.get(c.league), "league-logo", c.leagueName),
      el("span", { text: c.leagueName }),
    ]});
    const tr = el("tr", { className: "club-row", children: [
      el("td", { text: String(i + 1) }),
      clubCell,
      leagueCell,
      el("td", { text: String(c.playerCount) }),
      el("td", { className: "score", text: c.scores[currentView].toFixed(1) }),
    ]});
    const detail = el("tr", { className: "detail", children: [
      el("td", { attrs: { colspan: "5" }, children: [playersNode(c)] }),
    ]});
    detail.style.display = "none";
    tr.onclick = () => {
      detail.style.display = detail.style.display === "none" ? "" : "none";
    };
    nodes.push(tr, detail);
  });
  rows.replaceChildren(...nodes);
}

function playersNode(club) {
  const wrap = el("div", { className: "players" });
  club.players.forEach(p => {
    const parts = p.breakdown
      .map(b => `${b.label} ${b.points > 0 ? "+" : ""}${b.points}`)
      .join(", ");
    const metaChildren = [
      logoImg(p.nationFlag, "flag", p.nation),
      el("span", { text: `${p.position}, ${p.nation}, ${p.minutes}'` }),
    ];
    const left = el("span", { className: "player-left", children: [
      avatar(p),
      el("span", { children: [
        el("span", { className: "pname", text: p.name }),
        el("span", { className: "meta", children: metaChildren }),
      ]}),
    ]});
    const right = el("span", { children: [
      document.createTextNode(p.rating.toFixed(1) + " "),
      el("span", { className: "breakdown", text: parts }),
    ]});
    wrap.appendChild(el("div", { className: "player", children: [left, right] }));
  });
  return wrap;
}

function setupExplainer() {
  const btn = document.getElementById("explainer-toggle");
  const panel = document.getElementById("explainer");
  let built = false;
  btn.onclick = () => {
    if (!built) { panel.replaceChildren(explainerNode(DATA.methodology)); built = true; }
    panel.classList.toggle("hidden");
  };
}

function explainerNode(m) {
  const wrap = el("div", { className: "explainer-inner" });
  wrap.appendChild(el("h2", { text: "How scoring works" }));
  wrap.appendChild(el("p", {
    text: "Each player gets a position-aware rating from their World Cup match stats. "
        + "Clubs are then ranked four ways:",
  }));

  const views = el("ul", { className: "views" });
  m.views.forEach(v =>
    views.appendChild(el("li", { children: [
      el("strong", { text: v.label + ": " }),
      el("span", { text: v.formula }),
    ]})));
  wrap.appendChild(views);

  // Weights table: rows = stat labels, columns = position groups.
  const groups = ["GK", "DEF", "MID", "FWD"];
  const fields = Object.keys(m.fieldLabels);
  const table = el("table", { className: "weights" });
  const head = el("tr", { children: [
    el("th", { text: "Stat" }),
    ...groups.map(g => el("th", { text: g })),
  ]});
  table.appendChild(el("thead", { children: [head] }));
  const body = el("tbody");
  fields.forEach(f => {
    body.appendChild(el("tr", { children: [
      el("td", { text: m.fieldLabels[f] }),
      ...groups.map(g => {
        const v = m.weights[g][f];
        return el("td", { className: "num", text: v == null ? "" : String(v) });
      }),
    ]}));
  });
  // Clean sheet + appearance rows.
  body.appendChild(el("tr", { children: [
    el("td", { text: "Clean sheet" }),
    ...groups.map(g => el("td", { className: "num", text: String(m.cleanSheetBonus[g]) })),
  ]}));
  body.appendChild(el("tr", { children: [
    el("td", { text: "Appearance" }),
    ...groups.map(() => el("td", { className: "num", text: String(m.appearancePoints) })),
  ]}));
  table.appendChild(body);
  wrap.appendChild(table);

  const notes = el("ul", { className: "notes" });
  m.notes.forEach(n => notes.appendChild(el("li", { text: n })));
  wrap.appendChild(notes);
  return wrap;
}

load();
