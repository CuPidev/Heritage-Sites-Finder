function qs(key, fallback) {
    const params = new URLSearchParams(location.search);
    return params.has(key) ? params.get(key) : fallback;
}

let offset = parseInt(qs("offset", "0"), 10) || 0;
let limit = Math.min(100, Math.max(1, parseInt(qs("limit", "10"), 10) || 10));
const q = qs("q", "");
// preserve shuffle mode via URL param so reload keeps random results
let shuffleMode = qs("shuffle", "0") === "1";
let total = 0;

const controls = document.getElementById("controls");
const listEl = document.getElementById("list");
const pager = document.getElementById("pager");

function renderControls() {
    controls.innerHTML = "";
    const limitLabel = document.createElement("label");
    limitLabel.className = "text-sm text-gray-700";
    limitLabel.textContent = "Per page:";
    const limitSel = document.createElement("select");
    limitSel.className = "ml-2 border rounded px-2";
    [10, 20, 50, 100].forEach((n) => {
        const o = document.createElement("option");
        o.value = String(n);
        o.text = String(n);
        if (n === limit) o.selected = true;
        limitSel.appendChild(o);
    });
    limitSel.addEventListener("change", () => {
        limit = parseInt(limitSel.value, 10);
        offset = 0;
        loadPage(offset);
    });

    const shuffleBtn = document.createElement("button");
    // button appearance depends on shuffleMode
    function updateShuffleButton() {
        if (shuffleMode) {
            shuffleBtn.className =
                "ml-4 px-3 py-1 bg-blue-600 text-white rounded text-sm";
            shuffleBtn.textContent = "Stop shuffle";
        } else {
            shuffleBtn.className = "ml-4 px-3 py-1 bg-gray-200 rounded text-sm";
            shuffleBtn.textContent = "Shuffle";
        }
    }
    updateShuffleButton();
    shuffleBtn.addEventListener("click", () => {
        const u = new URL(window.location.href);
        if (!shuffleMode) {
            // turn shuffle ON: set param, update state, reload shuffled
            shuffleMode = true;
            u.searchParams.set("shuffle", "1");
            history.replaceState(null, "", u.toString());
            offset = 0;
            updateShuffleButton();
            loadPage(offset, true);
        } else {
            // turn shuffle OFF: remove param, update state, reload deterministic
            shuffleMode = false;
            u.searchParams.delete("shuffle");
            history.replaceState(null, "", u.toString());
            offset = 0;
            updateShuffleButton();
            loadPage(offset, false);
        }
    });

    controls.appendChild(limitLabel);
    controls.appendChild(limitSel);
    controls.appendChild(shuffleBtn);
}

function renderPager() {
    pager.innerHTML = "";
    const info = document.createElement("div");
    info.className = "text-sm text-gray-700";
    info.textContent = `Showing ${Math.min(total, offset + 1)}-${Math.min(
        total,
        offset + limit
    )} of ${total}`;

    const nav = document.createElement("div");
    nav.className = "space-x-2";
    const prev = document.createElement("button");
    prev.className = "px-3 py-1 bg-white border rounded text-sm";
    prev.textContent = "Prev";
    prev.disabled = offset === 0;
    prev.addEventListener("click", () => {
        offset = Math.max(0, offset - limit);
        loadPage(offset);
    });

    const next = document.createElement("button");
    next.className = "px-3 py-1 bg-white border rounded text-sm";
    next.textContent = "Next";
    next.disabled = offset + limit >= total;
    next.addEventListener("click", () => {
        if (offset + limit < total) {
            offset = offset + limit;
            loadPage(offset);
        }
    });

    nav.appendChild(prev);
    nav.appendChild(next);
    pager.appendChild(info);
    pager.appendChild(nav);
}

function renderList(items) {
    listEl.innerHTML = "";
    if (!items || items.length === 0) {
        listEl.textContent = "No items";
        return;
    }
    for (const it of items) {
        const d = document.createElement("div");
        d.className = "p-3 border-b bg-white rounded";
        d.innerHTML = `<div class=\"flex justify-between items-baseline\"><strong class=\"text-lg\">${
            it.name
        }</strong></div><div class=\"text-sm text-gray-600\">${
            it.country || ""
        }</div><div class=\"mt-1 text-sm\">${it.description || ""}</div>`;
        listEl.appendChild(d);
    }
}

async function loadPage(start = 0, shuffle = false) {
    const params = new URLSearchParams();
    params.set("offset", String(start));
    params.set("limit", String(limit));
    // if shuffle argument passed or shuffleMode active, request shuffled results
    const useShuffle = shuffle || shuffleMode;
    if (useShuffle) params.set("shuffle", "1");
    if (q) params.set("q", q);
    const url = `/browse?${params.toString()}`;
    try {
        const res = await fetch(url);
        if (!res.ok) {
            listEl.textContent = `Error: ${res.status} ${res.statusText}`;
            return;
        }
        const data = await res.json();
        total = data.total || 0;
        renderList(data.items || []);
        renderPager();
    } catch (err) {
        listEl.textContent = `Error: ${
            err && err.message ? err.message : String(err)
        }`;
    }
}

// initialize
renderControls();
loadPage(offset);
