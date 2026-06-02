/* ══════════════════════════════════════════
   api.js — shared fetch helpers
   Include in every page:
   <script src="../static/api.js"></script>
   ══════════════════════════════════════════ */

/**
 * Build a query string from a params object.
 * Values can be single values or arrays.
 * e.g. { level: [1,2], age: "18-21" }
 * → "level=1&level=2&age=18-21"
 */
function buildQuery(params) {
    const parts = [];
    for (const [key, val] of Object.entries(params)) {
        if (Array.isArray(val)) {
            val.forEach(v => parts.push(`${key}=${encodeURIComponent(v)}`));
        } else if (val !== null && val !== undefined && val !== "") {
            parts.push(`${key}=${encodeURIComponent(val)}`);
        }
    }
    return parts.length ? "?" + parts.join("&") : "";
}

async function fetchJSON(endpoint, params = {}) {
    const url = endpoint + buildQuery(params);
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API error ${res.status}: ${url}`);
    return res.json();
}

/* ── Page-specific API calls ── */

const API = {

    // Home page
    home: () => fetchJSON("/api/home"),

    // Filter options
    filterOptions: () => fetchJSON("/api/filter-options"),

    // People & Injury — stacked bar
    injurySummary: (levels = []) =>
        fetchJSON("/api/injury-summary", { level: levels }),

    // People & Injury — pictogram
    pictogram: (ages = [], levels = []) =>
        fetchJSON("/api/pictogram", { age: ages, level: levels }),

    // People & Injury — ejected table
    ejectedTable: (filters = {}) =>
        fetchJSON("/api/ejected-table", filters),

    // People Analysis
    peopleAnalysis: (filters = {}) =>
        fetchJSON("/api/people-analysis", filters),

};