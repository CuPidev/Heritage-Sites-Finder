// Helpers for UI state
const btn = document.getElementById("go");
const qInput = document.getElementById("q");
const kSelect = document.getElementById("k");
const spinner = document.getElementById("spinner");

function setLoading(loading) {
    btn.disabled = loading;
    qInput.disabled = loading;
    kSelect.disabled = loading;
    spinner.style.display = loading ? "inline-block" : "none";
    btn.textContent = loading ? "Searching…" : "Search";
}

// Persist k (results count) in localStorage so user's choice is remembered
const STORAGE_KEY = "hsf:k";
(function () {
    // debug flag: ?debug_showmore=1 will print measurements to console
    window.__HSF_DEBUG_SHOWMORE = new URL(location).searchParams.has(
        "debug_showmore"
    );
})();

// Minimum characters that should always get a Show more control
const MIN_SHOW_MORE_CHARS = 220;
(function restoreK() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) kSelect.value = saved;
    } catch (e) {
        // ignore if localStorage inaccessible
    }
})();
kSelect.addEventListener("change", () => {
    try {
        localStorage.setItem(STORAGE_KEY, kSelect.value);
    } catch (e) {
        // ignore quota / privacy mode errors
    }
});

async function search(q, k) {
    setLoading(true);
    try {
        const res = await fetch(
            `/search?q=${encodeURIComponent(q)}&k=${encodeURIComponent(k)}`
        );
        if (!res.ok) {
            const err = await res
                .json()
                .catch(() => ({ error: res.statusText }));
            document.getElementById("results").innerText =
                "Error: " + (err.error || res.statusText);
            return;
        }
        const data = await res.json();
        const el = document.getElementById("results");
        el.innerHTML = "";
        // toolbar: open full list in browse view
        if (q) {
            const toolbar = document.createElement("div");
            toolbar.className = "mb-3 flex items-center justify-end";
            const openBtn = document.createElement("a");
            openBtn.href = `/browse.html?q=${encodeURIComponent(
                q
            )}&limit=${encodeURIComponent(Math.max(10, k))}`;
            openBtn.className = "text-sm text-blue-600 mr-2";
            openBtn.textContent = "Open full list";
            toolbar.appendChild(openBtn);
            el.appendChild(toolbar);
        }
        if (!Array.isArray(data) || data.length === 0) {
            el.innerText = "No results";
            return;
        }

        // Helper: truncate long descriptions
        function truncate(str, n) {
            if (!str) return "";
            return str.length > n ? str.slice(0, n - 1) + "…" : str;
        }

        // escape HTML to avoid injection
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

        // highlight query terms (space separated) inside a text safely
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
            // replace on escaped text so it's safe
            return escaped.replace(re, '<span class="highlight">$1</span>');
        }

        for (const r of data) {
            const card = document.createElement("article");
            card.className = "result";

            // header: title + country / score
            const header = document.createElement("div");
            header.className = "result-header";

            const titleWrap = document.createElement("div");
            const title = document.createElement("div");
            title.className = "result-title";
            // highlight query terms in title
            title.innerHTML = highlightText(r.name || "(no title)", q);
            titleWrap.appendChild(title);

            const rightMeta = document.createElement("div");
            rightMeta.style.display = "flex";
            rightMeta.style.alignItems = "center";
            rightMeta.style.gap = "0.5rem";

            if (r.country) {
                const country = document.createElement("span");
                country.className = "country-badge";
                country.textContent = r.country;
                rightMeta.appendChild(country);
            }

            if (typeof r.score === "number") {
                const score = document.createElement("span");
                score.className = "score";
                score.textContent = `[${r.score.toFixed(3)}]`;
                rightMeta.appendChild(score);
            }

            header.appendChild(titleWrap);
            header.appendChild(rightMeta);
            card.appendChild(header);

            // description/snippet
            const desc = document.createElement("p");
            desc.className = "description";
            const fullText = r.description || "";
            const maxLen = 800;
            const shortText = truncate(fullText, maxLen);
            desc.innerHTML = highlightText(shortText, q);
            card.appendChild(desc);

            // optional meta line (e.g., id or other)
            const meta = document.createElement("div");
            meta.className = "meta";
            meta.textContent = r.id ? `id: ${r.id}` : "";
            card.appendChild(meta);

            // create Show more control (but decide visibility after measuring)
            let more = null;
            if (
                fullText &&
                (fullText.length > shortText.length ||
                    fullText.length >= MIN_SHOW_MORE_CHARS)
            ) {
                more = document.createElement("button");
                more.type = "button";
                more.className = "show-more";
                more.textContent = "Show more";
                // attach listener now
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
                // show immediately (hotfix): ensure Show more is visible for long items
                more.style.display = "";
                card.appendChild(more);
            }

            // append the card to DOM so measurements are correct
            el.appendChild(card);

            // measure whether the card's content actually overflows the collapsed card
            if (more) {
                // hide until we confirm overflow (prevents flicker)
                more.style.display = "none";

                // Use two rAFs to wait for layout/fonts to settle, then measure.
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        const rootFont =
                            parseFloat(
                                getComputedStyle(document.documentElement)
                                    .fontSize
                            ) || 16;
                        const overlayPx = rootFont * 2.6; // match CSS overlay height (2.6rem)
                        const descRect = desc.getBoundingClientRect();
                        const cardRect = card.getBoundingClientRect();
                        // If the description's bottom extends below the visible card bottom
                        // minus the overlay hint area, we consider it clipped.
                        const overflows =
                            descRect.bottom > cardRect.bottom - overlayPx - 2; // tolerance
                        if (overflows) {
                            more.style.display = "";
                        } else {
                            if (window.__HSF_DEBUG_SHOWMORE) {
                                console.debug(
                                    "HSF: no overflow (hotfix keep)",
                                    {
                                        title: r.name,
                                        cardClient: card.clientHeight,
                                        cardScroll: card.scrollHeight,
                                        descClient: desc.clientHeight,
                                        descScroll: desc.scrollHeight,
                                        descRect: desc.getBoundingClientRect(),
                                        cardRect: card.getBoundingClientRect(),
                                    }
                                );
                            }
                            /* hotfix: keep the Show more control visible even if measurement
                               thought there's no overflow. This guarantees the user can
                               expand long items like the Hegra description. */
                        }
                    });
                });

                // Fallback: if rAFs don't catch late font/layout changes, check again shortly
                setTimeout(() => {
                    if (!document.contains(more)) return;
                    if (more.style.display === "") return; // already shown
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
                        if (window.__HSF_DEBUG_SHOWMORE) {
                            console.debug(
                                "HSF(fallback): no overflow (hotfix keep)",
                                {
                                    title: r.name,
                                    cardClient: card.clientHeight,
                                    cardScroll: card.scrollHeight,
                                    descClient: desc.clientHeight,
                                    descScroll: desc.scrollHeight,
                                    descRect: desc.getBoundingClientRect(),
                                    cardRect: card.getBoundingClientRect(),
                                }
                            );
                        }
                        /* hotfix: keep button visible */
                    }
                }, 120);
            }
        }
    } catch (err) {
        document.getElementById("results").innerText =
            "Error: " + (err && err.message ? err.message : String(err));
    } finally {
        setLoading(false);
    }
}

btn.addEventListener("click", () => {
    const q = qInput.value.trim();
    const k = parseInt(kSelect.value || "10", 10);
    if (q) search(q, k);
});

qInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") btn.click();
});

// allow changing k via keyboard (Enter will trigger search)
kSelect.addEventListener("keydown", (e) => {
    if (e.key === "Enter") btn.click();
});
