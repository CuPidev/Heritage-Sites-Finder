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

// Minimum characters that should always get a Show more control
const MIN_SHOW_MORE_CHARS = 220;

const controls = document.getElementById("controls");
const listEl = document.getElementById("list");
const pager = document.getElementById("pager");

function renderControls() {
    controls.innerHTML = "";
    const limitLabel = document.createElement("label");
    limitLabel.className = "text-sm text-gray-700 mr-2";
    limitLabel.textContent = "Per page:";

    const limitSel = document.createElement("select");
    limitSel.className = "ml-2 border rounded px-2";
    [10, 20, 50, 100].forEach((n) => {
        const opt = document.createElement("option");
        opt.value = String(n);
        opt.textContent = String(n);
        if (n === limit) opt.selected = true;
        limitSel.appendChild(opt);
    });
    limitSel.addEventListener("change", () => {
        limit = parseInt(limitSel.value, 10) || limit;
        offset = 0;
        const u = new URL(location);
        u.searchParams.set("limit", String(limit));
        u.searchParams.set("offset", "0");
        history.replaceState(null, "", u.toString());
        loadPage(0);
    });

    // shuffle toggle
    const shuffleBtn = document.createElement("button");
    shuffleBtn.className = "px-3 py-1 bg-white border rounded text-sm ml-3";
    function updateShuffleButton() {
        shuffleBtn.textContent = shuffleMode ? "Shuffle: ON" : "Shuffle: OFF";
        shuffleBtn.setAttribute("aria-pressed", shuffleMode ? "true" : "false");
    }
    shuffleBtn.addEventListener("click", () => {
        shuffleMode = !shuffleMode;
        const u = new URL(location);
        if (shuffleMode) u.searchParams.set("shuffle", "1");
        else u.searchParams.delete("shuffle");
        u.searchParams.set("offset", "0");
        history.replaceState(null, "", u.toString());
        offset = 0;
        updateShuffleButton();
        loadPage(0, shuffleMode);
    });

    updateShuffleButton();

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
    // helpers for safe highlighting and truncation
    function truncate(str, n) {
        if (!str) return "";
        return str.length > n ? str.slice(0, n - 1) + "…" : str;
    }
    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }
    function escapeRegex(s) {
        return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }
    function highlightText(text, query) {
        if (!text) return "";
        const escaped = escapeHtml(text);
        if (!query) return escaped;
        const tokens = query
            .split(/\s+/)
            .map((t) => t.trim())
            .filter(Boolean)
            .map(escapeRegex);
        if (tokens.length === 0) return escaped;
        const re = new RegExp("(" + tokens.join("|") + ")", "ig");
        return escaped.replace(re, '<span class="highlight">$1</span>');
    }

    for (const it of items) {
        const card = document.createElement("article");
        card.className = "result";

        const header = document.createElement("div");
        header.className = "result-header";
        const title = document.createElement("div");
        title.className = "result-title";
        title.innerHTML = highlightText(it.name || "(no title)", q);
        header.appendChild(title);

        const rightMeta = document.createElement("div");
        rightMeta.style.display = "flex";
        rightMeta.style.alignItems = "center";
        rightMeta.style.gap = "0.5rem";
        if (it.country) {
            const country = document.createElement("span");
            country.className = "country-badge";
            country.textContent = it.country;
            rightMeta.appendChild(country);
        }
        header.appendChild(rightMeta);
        card.appendChild(header);

        const fullText = it.description || "";
        const maxLen = 400; // slightly shorter in browse list
        const shortText = truncate(fullText, maxLen);
        const desc = document.createElement("p");
        desc.className = "description";
        desc.innerHTML = highlightText(shortText, q);
        card.appendChild(desc);

        if (
            fullText &&
            (fullText.length > maxLen || fullText.length >= MIN_SHOW_MORE_CHARS)
        ) {
            const more = document.createElement("button");
            more.type = "button";
            more.className = "show-more";
            more.textContent = "Show more";
            let expanded = false;
            more.addEventListener("click", () => {
                expanded = !expanded;
                if (expanded) {
                    desc.innerHTML = highlightText(fullText, q);
                    more.textContent = "Show less";
                    card.classList.add("expanded");
                } else {
                    desc.innerHTML = highlightText(shortText, q);
                    more.textContent = "Show more";
                    card.classList.remove("expanded");
                }
            });
            // show immediately (hotfix) so users can expand long items like Hegra
            more.style.display = "";
            card.appendChild(more);

            // measure after layout stabilizes (double rAF) and show/remove accordingly
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    const rootFont =
                        parseFloat(
                            getComputedStyle(document.documentElement).fontSize
                        ) || 16;
                    const overlayPx = rootFont * 2.6;
                    const descRect = desc.getBoundingClientRect();
                    const cardRect = card.getBoundingClientRect();
                    const overflows =
                        descRect.bottom > cardRect.bottom - overlayPx - 2;
                    if (overflows) {
                        more.style.display = "";
                    } else {
                        if (
                            new URL(location).searchParams.has("debug_showmore")
                        ) {
                            console.debug(
                                "HSF: browse no overflow (hotfix keep)",
                                {
                                    title: it.name,
                                    cardClient: card.clientHeight,
                                    cardScroll: card.scrollHeight,
                                    descClient: desc.clientHeight,
                                    descScroll: desc.scrollHeight,
                                    descRect,
                                    cardRect,
                                }
                            );
                        }
                        /* hotfix: keep the Show more control visible to guarantee expandability */
                    }
                });
            });

            // fallback check
            setTimeout(() => {
                if (!document.contains(more)) return;
                if (more.style.display === "") return;
                const rootFont =
                    parseFloat(
                        getComputedStyle(document.documentElement).fontSize
                    ) || 16;
                const overlayPx = rootFont * 2.6;
                const descRect = desc.getBoundingClientRect();
                const cardRect = card.getBoundingClientRect();
                const overflows =
                    descRect.bottom > cardRect.bottom - overlayPx - 2;
                if (overflows) more.style.display = "";
                else if (document.contains(more)) {
                    if (new URL(location).searchParams.has("debug_showmore")) {
                        console.debug(
                            "HSF(fallback): browse no overflow (hotfix keep)",
                            {
                                title: it.name,
                                cardClient: card.clientHeight,
                                cardScroll: card.scrollHeight,
                                descClient: desc.clientHeight,
                                descScroll: desc.scrollHeight,
                            }
                        );
                    }
                    /* hotfix: keep Show more visible */
                }
            }, 120);
        }

        listEl.appendChild(card);
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
