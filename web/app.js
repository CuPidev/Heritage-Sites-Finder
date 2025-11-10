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
        if (!Array.isArray(data) || data.length === 0) {
            el.innerText = "No results";
            return;
        }
        for (const r of data) {
            const d = document.createElement("div");
            d.className = "result";
            d.innerHTML = `<div><strong>${
                r.name
            }</strong> <span class="score">[${r.score.toFixed(
                4
            )}]</span></div><div>${r.country || ""}</div><div>${
                r.description || ""
            }</div>`;
            el.appendChild(d);
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
