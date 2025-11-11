import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ResultsCard from "../components/ResultsCard";

function qs(key: string, fallback?: string) {
    const params = new URLSearchParams(location.search);
    return params.has(key) ? params.get(key) : fallback;
}

const MIN_SHOW_MORE_CHARS = 220;

export default function BrowsePage() {
    const [offset, setOffset] = useState(
        () => parseInt(qs("offset", "0") || "0", 10) || 0
    );
    const [limit, setLimit] = useState(() =>
        Math.min(
            100,
            Math.max(1, parseInt(qs("limit", "10") || "10", 10) || 10)
        )
    );
    const [q] = useState(() => qs("q", "") || "");
    const [shuffleMode, setShuffleMode] = useState(
        () => qs("shuffle", "0") === "1"
    );
    const [total, setTotal] = useState(0);
    const [items, setItems] = useState<any[]>([]);

    useEffect(() => {
        loadPage(offset, false);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    function updateUrl(params: Record<string, string>) {
        const u = new URL(location as any);
        Object.entries(params).forEach(([k, v]) => {
            if (v === "" || v == null) u.searchParams.delete(k);
            else u.searchParams.set(k, v);
        });
        history.replaceState(null, "", u.toString());
    }

    async function loadPage(start = 0, shuffle = false) {
        const params = new URLSearchParams();
        params.set("offset", String(start));
        params.set("limit", String(limit));
        const useShuffle = shuffle || shuffleMode;
        if (useShuffle) params.set("shuffle", "1");
        if (q) params.set("q", q);
        const url = `/browse?${params.toString()}`;
        try {
            const res = await fetch(url);
            if (!res.ok) {
                setItems([]);
                return;
            }
            const data = await res.json();
            setTotal(data.total || 0);
            setItems(data.items || []);
            setOffset(start);
        } catch (err) {
            setItems([]);
        }
    }

    function onLimitChange(n: number) {
        setLimit(n);
        setOffset(0);
        updateUrl({ limit: String(n), offset: "0" });
        loadPage(0);
    }

    function toggleShuffle() {
        const next = !shuffleMode;
        setShuffleMode(next);
        const u = new URL(location as any);
        if (next) u.searchParams.set("shuffle", "1");
        else u.searchParams.delete("shuffle");
        u.searchParams.set("offset", "0");
        history.replaceState(null, "", u.toString());
        setOffset(0);
        loadPage(0, next);
    }

    return (
        <div>
            <div className="mb-3">
                <Link
                    to="/"
                    className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800"
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                    >
                        <path d="M15 18l-6-6 6-6"></path>
                    </svg>
                    <span className="text-sm font-medium">Back</span>
                </Link>
            </div>

            <div id="controls" className="flex items-center gap-3 mb-4">
                <label className="text-sm text-gray-700 mr-2">Per page:</label>
                <select
                    value={String(limit)}
                    onChange={(e) =>
                        onLimitChange(parseInt(e.target.value, 10) || limit)
                    }
                    className="ml-2 border rounded px-2"
                >
                    {[10, 20, 50, 100].map((n) => (
                        <option key={n} value={String(n)}>
                            {n}
                        </option>
                    ))}
                </select>

                <button
                    className="px-3 py-1 bg-white border rounded text-sm ml-3"
                    onClick={toggleShuffle}
                    aria-pressed={shuffleMode}
                >
                    {shuffleMode ? "Shuffle: ON" : "Shuffle: OFF"}
                </button>
            </div>

            <div id="list" className="space-y-2">
                {items.length === 0 && <div>No items</div>}
                {items.map((it, i) => (
                    <ResultsCard key={i} item={it} query={q} maxLen={400} />
                ))}
            </div>

            <div id="pager" className="mt-4 flex items-center justify-between">
                <div className="text-sm text-gray-700">
                    Showing {Math.min(total, offset + 1)}-
                    {Math.min(total, offset + limit)} of {total}
                </div>
                <div className="space-x-2">
                    <button
                        className="px-3 py-1 bg-white border rounded text-sm"
                        onClick={() => {
                            const n = Math.max(0, offset - limit);
                            setOffset(n);
                            loadPage(n);
                        }}
                        disabled={offset === 0}
                    >
                        Prev
                    </button>
                    <button
                        className="px-3 py-1 bg-white border rounded text-sm"
                        onClick={() => {
                            const n = offset + limit;
                            if (n < total) {
                                setOffset(n);
                                loadPage(n);
                            }
                        }}
                        disabled={offset + limit >= total}
                    >
                        Next
                    </button>
                </div>
            </div>
        </div>
    );
}
