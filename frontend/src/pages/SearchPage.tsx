import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ResultsCard from "../components/ResultsCard";

export default function SearchPage() {
    const [q, setQ] = useState("");
    const [k, setK] = useState(() => {
        try {
            return localStorage.getItem("hsf:k") || "10";
        } catch (e) {
            return "10";
        }
    });
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<any[]>([]);

    useEffect(() => {
        try {
            localStorage.setItem("hsf:k", k);
        } catch (e) {}
    }, [k]);

    async function doSearch() {
        const tq = q.trim();
        if (!tq) return;
        setLoading(true);
        try {
            const res = await fetch(
                `/search?q=${encodeURIComponent(tq)}&k=${encodeURIComponent(k)}`
            );
            if (!res.ok) {
                setResults([]);
                return;
            }
            const data = await res.json();
            setResults(Array.isArray(data) ? data : []);
        } catch (err) {
            setResults([]);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div>
            <div className="mb-4 flex justify-center sm:justify-start">
                <Link
                    to="/browse?shuffle=1"
                    className="inline-flex items-center gap-2 border border-blue-600 text-blue-600 px-3 py-2 rounded-lg hover:bg-blue-50"
                >
                    <span className="font-medium text-sm">
                        I want to browse instead
                    </span>
                </Link>
            </div>

            <div className="mb-4 flex flex-col sm:flex-row items-start sm:items-center gap-2">
                <div className="flex items-center gap-2 w-full">
                    <input
                        id="q"
                        value={q}
                        onChange={(e) => setQ(e.target.value)}
                        type="text"
                        autoFocus
                        placeholder="type here e.g. old castle"
                        className="border-2 border-gray-300 bg-white rounded px-3 h-10 flex-1 min-w-0 focus:outline-none focus:ring-4 focus:ring-blue-300 focus:border-blue-600 shadow-sm"
                    />
                    <label htmlFor="k" className="sr-only">
                        Results
                    </label>
                    <select
                        id="k"
                        value={k}
                        onChange={(e) => setK(e.target.value)}
                        className="border-2 border-gray-300 bg-white rounded px-2 h-10 w-20 focus:outline-none focus:ring-4 focus:ring-blue-300 focus:border-blue-600 shadow-sm"
                    >
                        <option value="5">5</option>
                        <option value="10">10</option>
                        <option value="20">20</option>
                        <option value="50">50</option>
                    </select>
                </div>

                <div className="w-full sm:w-auto">
                    <button
                        id="go"
                        onClick={doSearch}
                        disabled={loading}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 w-full sm:w-auto"
                    >
                        {loading ? "Searching…" : "Search"}
                    </button>
                </div>

                <div className="flex items-center">
                    <span
                        id="spinner"
                        className="spinner ml-2"
                        style={{ display: loading ? "inline-block" : "none" }}
                        aria-hidden="true"
                    />
                </div>
            </div>

            <div id="results" className="mt-4">
                {q && (
                    <div className="mb-3 flex items-center justify-end">
                        <Link
                            to={`/browse?q=${encodeURIComponent(
                                q
                            )}&limit=${encodeURIComponent(
                                Math.max(10, parseInt(k, 10) || 10)
                            )}`}
                            className="text-sm text-blue-600 mr-2"
                        >
                            Open full list
                        </Link>
                    </div>
                )}

                {results.length === 0 && <div>No results</div>}

                <div className="space-y-3">
                    {results.map((r, i) => (
                        <ResultsCard key={i} item={r} query={q} />
                    ))}
                </div>
            </div>
        </div>
    );
}
