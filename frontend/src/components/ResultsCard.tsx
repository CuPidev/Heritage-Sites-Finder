import React, { useMemo, useState } from "react";

const MIN_SHOW_MORE_CHARS = 220;

function escapeHtml(s: string) {
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function escapeRegex(s: string) {
    return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightText(text: string, query?: string) {
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

export default function ResultsCard({ item, query, maxLen = 800 }: any) {
    const fullText: string = item.description || "";
    const shortText =
        fullText.length > maxLen
            ? fullText.slice(0, maxLen - 1) + "…"
            : fullText;
    const shouldHaveToggle =
        fullText &&
        (fullText.length > shortText.length ||
            fullText.length >= MIN_SHOW_MORE_CHARS);
    const [expanded, setExpanded] = useState(false);

    const displayedHtml = useMemo(() => {
        return highlightText(expanded ? fullText : shortText, query);
    }, [expanded, fullText, shortText, query]);

    return (
        <article
            className={"result" + (expanded ? " expanded" : "")}
            tabIndex={0}
            aria-labelledby={item.id ? `title-${item.id}` : undefined}
        >
            <div className="result-header">
                <div>
                    <div
                        id={item.id ? `title-${item.id}` : undefined}
                        className="result-title"
                        dangerouslySetInnerHTML={{
                            __html: highlightText(
                                item.name || "(no title)",
                                query
                            ),
                        }}
                    />
                </div>
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                    }}
                >
                    {item.country && (
                        <span className="country-badge">{item.country}</span>
                    )}
                    {typeof item.score === "number" && (
                        <span className="score">[{item.score.toFixed(3)}]</span>
                    )}
                </div>
            </div>

            <p
                className="description"
                dangerouslySetInnerHTML={{ __html: displayedHtml }}
            />

            <div className="meta">{item.id ? `id: ${item.id}` : ""}</div>

            {shouldHaveToggle && (
                <button
                    type="button"
                    className="show-more"
                    onClick={() => setExpanded((s) => !s)}
                >
                    {expanded ? "Show less" : "Show more"}
                </button>
            )}
        </article>
    );
}
