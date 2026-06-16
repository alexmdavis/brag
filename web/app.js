const VIEWS = [
  { key: "total", label: "Total" },
  { key: "average", label: "Average" },
  { key: "per90", label: "Per-90" },
  { key: "bestXI", label: "Best XI" },
];

let DATA = null;
let currentLeague = "all";
let currentView = "total";

// Safe element builder. Text is always set via textContent, never innerHTML,
// so external data (player/club/nation names) cannot inject markup.
function el(tag, opts = {}) {
  const node = document.createElement(tag);
  if (opts.className) node.className = opts.className;
  if (opts.text != null) node.textContent = opts.text;
  if (opts.attrs) {
    for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
  }
  (opts.children || []).forEach(c => node.appendChild(c));
  return node;
}

async function load() {
  const res = await fetch("standings.json", { cache: "no-store" });
  DATA = await res.json();
  buildLeagueTabs();
  buildViewTabs();
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
  wrap.replaceChildren(...leagues().map(([key, name]) => {
    const b = el("button", { text: name, className: key === currentLeague ? "active" : "" });
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

  const clubs = DATA.clubs
    .filter(c => currentLeague === "all" || c.league === currentLeague)
    .slice()
    .sort((a, b) => b.scores[currentView] - a.scores[currentView]);

  const nodes = [];
  clubs.forEach((c, i) => {
    const tr = el("tr", { className: "club-row", children: [
      el("td", { text: String(i + 1) }),
      el("td", { text: c.club }),
      el("td", { text: c.leagueName }),
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
    const left = el("span", { children: [
      document.createTextNode(p.name + " "),
      el("span", { className: "meta", text: `(${p.position}, ${p.nation}, ${p.minutes}')` }),
    ]});
    const right = el("span", { children: [
      document.createTextNode(p.rating.toFixed(1) + " "),
      el("span", { className: "breakdown", text: parts }),
    ]});
    wrap.appendChild(el("div", { className: "player", children: [left, right] }));
  });
  return wrap;
}

load();
