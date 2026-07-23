const CATEGORY_CLASS = {
  "ISO/RTO": "iso",
  "Regulatory": "reg",
  "Trade Press": "iso",
  "Data Centers & Load Growth": "dc",
  "DER & Grid Modernization": "der",
};

let ALL_ARTICLES = [];
let ACTIVE_CATEGORY = "all";

function timeAgo(iso) {
  const then = new Date(iso);
  const diffMs = Date.now() - then.getTime();
  const hrs = Math.round(diffMs / 3.6e6);
  if (hrs < 1) return "just now";
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  return `${days}d ago`;
}

function render() {
  const grid = document.getElementById("articleGrid");
  const query = document.getElementById("searchBox").value.trim().toLowerCase();

  let items = ALL_ARTICLES;
  if (ACTIVE_CATEGORY !== "all") {
    items = items.filter(a => a.category === ACTIVE_CATEGORY);
  }
  if (query) {
    items = items.filter(a =>
      a.title.toLowerCase().includes(query) ||
      a.source.toLowerCase().includes(query) ||
      (a.summary || "").toLowerCase().includes(query)
    );
  }

  if (items.length === 0) {
    grid.innerHTML = `<p class="empty">No articles match. Try a different filter or search term.</p>`;
    return;
  }

  grid.innerHTML = items.map(a => `
    <article class="card">
      <div class="card-meta">
        <span class="card-category ${CATEGORY_CLASS[a.category] || ''}">${a.category}</span>
        <span>${timeAgo(a.published)}</span>
      </div>
      <h3><a href="${a.link}" target="_blank" rel="noopener">${escapeHtml(a.title)}</a></h3>
      ${a.summary ? `<p>${escapeHtml(a.summary)}</p>` : ""}
      <div class="card-source">${escapeHtml(a.source)}</div>
    </article>
  `).join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function buildTabs(categories) {
  const tabsEl = document.getElementById("filterTabs");
  categories.forEach(cat => {
    const btn = document.createElement("button");
    btn.className = "tab";
    btn.textContent = cat;
    btn.dataset.category = cat;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
      btn.classList.add("active");
      ACTIVE_CATEGORY = cat;
      render();
    });
    tabsEl.appendChild(btn);
  });

  document.querySelector('.tab[data-category="all"]').addEventListener("click", (e) => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    e.target.classList.add("active");
    ACTIVE_CATEGORY = "all";
    render();
  });
}

async function init() {
  try {
    const res = await fetch("data/articles.json", { cache: "no-store" });
    const data = await res.json();
    ALL_ARTICLES = data.articles || [];

    document.getElementById("statCount").textContent = `${data.count} articles tracked`;
    document.getElementById("statUpdated").textContent =
      `last updated ${new Date(data.generated_at).toLocaleString()}`;

    const categories = [...new Set(ALL_ARTICLES.map(a => a.category))].sort();
    buildTabs(categories);
    render();
  } catch (e) {
    document.getElementById("articleGrid").innerHTML =
      `<p class="empty">Couldn't load feed data yet. If this is a fresh repo, run the "Update Energy Pulse" workflow once from the Actions tab.</p>`;
    console.error(e);
  }

  document.getElementById("searchBox").addEventListener("input", render);
}

init();
