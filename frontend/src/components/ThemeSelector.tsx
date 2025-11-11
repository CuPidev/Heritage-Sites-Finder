import React, { useEffect, useState } from "react";

const THEMES = [
    { id: "teal", label: "Teal" },
    { id: "indigo", label: "Indigo" },
    { id: "terracotta", label: "Warm" },
    { id: "olive", label: "Olive" },
];
const STORAGE_KEY = "hsf:theme";

export default function ThemeSelector() {
    const [value, setValue] = useState(() => {
        try {
            return localStorage.getItem(STORAGE_KEY) || THEMES[0].id;
        } catch (e) {
            return THEMES[0].id;
        }
    });

    useEffect(() => {
        const root = document.documentElement;
        THEMES.forEach((t) => root.classList.remove("theme-" + t.id));
        if (value) root.classList.add("theme-" + value);
        try {
            localStorage.setItem(STORAGE_KEY, value);
        } catch (e) {}
    }, [value]);

    return (
        <select
            id="theme-select"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="ml-2 border rounded px-2 py-1 text-sm"
        >
            {THEMES.map((t) => (
                <option key={t.id} value={t.id}>
                    {t.label}
                </option>
            ))}
        </select>
    );
}
