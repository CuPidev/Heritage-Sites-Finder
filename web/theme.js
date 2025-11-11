// Theme switcher for Heritage Sites Finder
(function () {
    const THEMES = [
        { id: "teal", label: "Teal" },
        { id: "indigo", label: "Indigo" },
        { id: "terracotta", label: "Warm" },
        { id: "olive", label: "Olive" },
    ];
    const STORAGE_KEY = "hsf:theme";

    function applyTheme(id) {
        const root = document.documentElement;
        THEMES.forEach((t) => root.classList.remove("theme-" + t.id));
        if (id) root.classList.add("theme-" + id);
        try {
            localStorage.setItem(STORAGE_KEY, id);
        } catch (e) {}
    }

    function initControl() {
        const el = document.getElementById("theme-select");
        if (!el) return;
        // populate
        el.innerHTML = "";
        for (const t of THEMES) {
            const opt = document.createElement("option");
            opt.value = t.id;
            opt.textContent = t.label;
            el.appendChild(opt);
        }
        const saved =
            (function () {
                try {
                    return localStorage.getItem(STORAGE_KEY);
                } catch (e) {
                    return null;
                }
            })() || THEMES[0].id;
        el.value = saved;
        applyTheme(saved);
        el.addEventListener("change", () => applyTheme(el.value));
    }

    // On DOM ready, initialize control if present
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initControl);
    } else {
        initControl();
    }
})();
