"""
db_level3.py — Level 3 queries (People Analysis + Accident Analysis pages)
Deep analysis: injury rates, cross-tabulations, correlations
"""

import sqlite3
import os

DB_PATH = "database/Road_Accidents.db"


def query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ══════════════════════════════════════════
#  PEOPLE ANALYSIS PAGE
# ══════════════════════════════════════════

def people_analysis(filters=None):
    """
    Analyzes person data by calculating proper injury rates and group totals.
    Fixes the filter binding mismatch and maps descriptions cleanly.
    """
    filters = filters or {}
    
    # ── 1. DYNAMIC WHERE CLAUSE BUILDER WITH EXPLICIT KEY CHECKING ──
    where_clauses = [
        "p.INJ_LEVEL IS NOT NULL",
        "a.SPEED_ZONE NOT IN (0, 777, 888, 999)"
    ]
    params = []

    # Safe array checking to ensure lists are parsed properly from http params
    if "level" in filters and filters["level"]:
        levels = filters["level"] if isinstance(filters["level"], list) else [filters["level"]]
        ph = ",".join("?" * len(levels))
        where_clauses.append(f"p.INJ_LEVEL IN ({ph})")
        params += [int(v) for v in levels]

    if "age" in filters and filters["age"]:
        ages = filters["age"] if isinstance(filters["age"], list) else [filters["age"]]
        ph = ",".join("?" * len(ages))
        where_clauses.append(f"p.AGE_GROUP IN ({ph})")
        params += [str(v) for v in ages]

    if "light" in filters and filters["light"]:
        lights = filters["light"] if isinstance(filters["light"], list) else [filters["light"]]
        ph = ",".join("?" * len(lights))
        where_clauses.append(f"a.LIGHT_CONDITION IN ({ph})")
        params += [int(v) for v in lights]

    where = "WHERE " + " AND ".join(where_clauses)

    # ── 2. GROUP BY BASE METRICS (TO GET ACCURATE PERCENTAGES) ──
    # do NOT group by p.INJ_LEVEL inside SQL, otherwise injury_rate becomes binary (100 or 0).
    # aggregate the total people in this specific environment block.
    rows = query(f"""
    SELECT
        CASE WHEN p.AGE_GROUP = '5-Dec' THEN '5-12' ELSE p.AGE_GROUP END AS age,
        p.ROAD_USER_TYPE as person_type_id,
        a.SPEED_ZONE AS speed_zone,
        a.LIGHT_CONDITION as light_id,
        ROUND(100.0 * SUM(CASE WHEN p.INJ_LEVEL = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS injury_rate,
        COUNT(*) AS total
    FROM Person p
    JOIN Accident a ON p.ACCIDENT_NO = a.ACCIDENT_NO
    {where}
    GROUP BY p.AGE_GROUP, p.ROAD_USER_TYPE, a.SPEED_ZONE, a.LIGHT_CONDITION
    HAVING total > 10
    ORDER BY injury_rate DESC
    """, params)

    if not rows:
        return []

    # ── 3. IN-MEMORY LABELS TRANSLATION (ZERO HARD DRIVE OVERHEAD) ──
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT ROAD_USER_TYPE, ROAD_USER_TYPE_DESC FROM Road_User")
    ru_map = {r["ROAD_USER_TYPE"]: r["ROAD_USER_TYPE_DESC"] for r in cur.fetchall()}

    cur.execute("SELECT COND_ID, COND_NAME FROM Light_Condition")
    lc_map = {r["COND_ID"]: r["COND_NAME"] for r in cur.fetchall()}
    conn.close()

    # Calculate overall baseline statistics
    avg = sum(r["injury_rate"] for r in rows) / len(rows)
    
    for r in rows:
        # Resolve text names using fast key hashes
        r["person_type"] = ru_map.get(r["person_type_id"], "Unknown")
        r["light_condition"] = lc_map.get(r["light_id"], "Unknown")
        
        # Inject the Total people count directly into the Injury text string column
        # This solves the requirement so users immediately see the data sample weight
        r["injury"] = f"Group Base Size: {r['total']} people"
        
        # Calculate standard mathematical deviations (+/- pp)
        diff = round(r["injury_rate"] - avg, 1)
        r["above"]       = f"+{diff}pp" if diff >= 0 else f"{diff}pp"
        r["above_class"] = "positive" if diff >= 0 else "negative"

    return rows



def people_analysis_chart(filters=None):
    """
    Aggregated injury rate per age group for the bar chart.
    Optimized to run a fast single-table aggregate footprint.
    """
    filters = filters or {}
    where_clauses = ["p.INJ_LEVEL IS NOT NULL"]
    params = []

    if filters.get("level"):
        ph = ",".join("?" * len(filters["level"]))
        where_clauses.append(f"p.INJ_LEVEL IN ({ph})")
        params += [int(v) for v in filters["level"]]

    if filters.get("age"):
        ph = ",".join("?" * len(filters["age"]))
        where_clauses.append(f"p.AGE_GROUP IN ({ph})")
        params += list(filters["age"])

    # If filtering by light, we need the Accident join; otherwise keep it single-table!
    join_clause = ""
    if filters.get("light"):
        join_clause = "JOIN Accident a ON p.ACCIDENT_NO = a.ACCIDENT_NO"
        ph = ",".join("?" * len(filters["light"]))
        where_clauses.append(f"a.LIGHT_CONDITION IN ({ph})")
        params += [int(v) for v in filters["light"]]

    where = "WHERE " + " AND ".join(where_clauses)

    return query(f"""
        SELECT
            CASE WHEN p.AGE_GROUP = '5-Dec' THEN '5-12' ELSE p.AGE_GROUP END AS age,     
            ROUND(100.0 * SUM(CASE WHEN p.INJ_LEVEL = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS injury_rate
        FROM Person p
        {join_clause}
        {where}
        GROUP BY p.AGE_GROUP
        ORDER BY age ASC
    """, params)



# ══════════════════════════════════════════
#  ACCIDENT ANALYSIS PAGE
# ══════════════════════════════════════════
_filter_options_cache = None

def get_accident_analysis(postcode=None, light=None, atmo=None, road=None):
    """
    Table + chart data for accident analysis page.
    Ensures safe token parameter bounds across all separate execution steps.
    """
    global _filter_options_cache
    
    # ── 1. DYNAMIC WHERE CLAUSE BUILDER ──
    where_clauses = ["1=1"]
    params = []
    node_join = ""
    atmo_join = ""
    road_join = ""

    # Postcode Filter
    if postcode:
        node_join = "JOIN Node n ON a.NODE_ID = n.NODE_ID"
        where_clauses.append("n.POSTCODE = ?")
        params.append(int(postcode))

    # Light Condition Filter
    if light:
        ph = ",".join("?" * len(light))
        where_clauses.append(f"lc.COND_NAME IN ({ph})")
        params += light

    # Atmospheric Condition Filter
    if atmo:
        atmo_join = """
            JOIN Atmospheric_Cond_Seq acs_f ON a.ACCIDENT_NO = acs_f.ACCIDENT_NO AND acs_f.ATMOSPH_COND_SEQ = 1
            JOIN Amospheric_Cond ac_f ON acs_f.ATMOSPH_COND = ac_f.ATMOSPH_COND
        """
        ph = ",".join("?" * len(atmo))
        where_clauses.append(f"ac_f.ATMOSPH_COND_DESC IN ({ph})")
        params += atmo

    # Road Surface Condition Filter
    if road:
        road_join = "JOIN Road_Surface_Cond rsc_f ON a.ACCIDENT_NO = rsc_f.ACCIDENT_NO"
        ph = ",".join("?" * len(road))
        where_clauses.append(f"rsc_f.SURFACE_COND_DESC IN ({ph})")
        params += road

    where = "WHERE " + " AND ".join(where_clauses)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── 2. VALIDIATE DROPDOWN VALUE CACHE ONCE ──
    if _filter_options_cache is None:
        cur.execute("SELECT DISTINCT COND_NAME FROM Light_Condition WHERE COND_NAME IS NOT NULL ORDER BY COND_NAME")
        light_opts = [r["COND_NAME"] for r in cur.fetchall()]
        
        cur.execute("SELECT DISTINCT SURFACE_COND_DESC FROM Road_Surface_Cond WHERE SURFACE_COND_DESC IS NOT NULL ORDER BY SURFACE_COND_DESC")
        road_opts = [r["SURFACE_COND_DESC"] for r in cur.fetchall()]
        
        cur.execute("SELECT DISTINCT ATMOSPH_COND_DESC FROM Amospheric_Cond WHERE ATMOSPH_COND_DESC IS NOT NULL ORDER BY ATMOSPH_COND_DESC")
        atmo_opts = [r["ATMOSPH_COND_DESC"] for r in cur.fetchall()]
        
        _filter_options_cache = {"light": light_opts, "atmo": atmo_opts, "road": road_opts}

    # ── 3. QUERY TABLE DATA (CAPPED AT 200 ROWS FOR PERFORMANCE) ──
    cur.execute(f"""
        SELECT
            a.ACCIDENT_NO,
            lc.COND_NAME                        AS light,
            a.ROAD_TYPE                         AS road_type,
            a.ROAD_NAME_INT                     AS intersection,
            a.NO_PERSONS                        AS people,
            a.ACCIDENT_DATE                     AS date,
            a.ACCIDENT_TIME                     AS time,
            COALESCE(ac.ATMOSPH_COND_DESC, '—') AS atmo
        FROM Accident a
        {node_join}
        {atmo_join}
        {road_join}
        JOIN Light_Condition lc ON a.LIGHT_CONDITION = lc.COND_ID
        LEFT JOIN Atmospheric_Cond_Seq acs ON a.ACCIDENT_NO = acs.ACCIDENT_NO AND acs.ATMOSPH_COND_SEQ = 1
        LEFT JOIN Amospheric_Cond ac ON acs.ATMOSPH_COND = ac.ATMOSPH_COND
        {where}
        ORDER BY a.ACCIDENT_DATE DESC
        LIMIT 200
    """, params)
    
    table_rows = [dict(r) for r in cur.fetchall()]

    for i, r in enumerate(table_rows, start=1):
        r["serial"] = i
        r["road"] = r.get("road_type") or "—"
        date_str = r["date"] or ""
        r["year"] = date_str[-4:] if len(date_str) >= 4 else "Unknown"

    # ── 4. QUERY PIE CHART DATA (PASSING THE PARAMS CORRECTLY!) ──
    cur.execute(f"""
        SELECT a.ROAD_TYPE, COUNT(*) as total
        FROM Accident a
        {node_join}
        {atmo_join}
        {road_join}
        JOIN Light_Condition lc ON a.LIGHT_CONDITION = lc.COND_ID
        {where}
        GROUP BY a.ROAD_TYPE
    """, params) # <-- Crucial fix: Added 'params' tokens bounding
    
    pie_labels = []
    pie_values = []
    for r in cur.fetchall():
        pie_labels.append(r["ROAD_TYPE"] or "Unknown")
        pie_values.append(r["total"])

    # ── 5. QUERY LINE CHART DATA (PASSING THE PARAMS CORRECTLY!) ──
    cur.execute(f"""
        SELECT SUBSTR(a.ACCIDENT_DATE, -4, 4) AS yr, COUNT(*) as total
        FROM Accident a
        {node_join}
        {atmo_join}
        {road_join}
        {where}
        GROUP BY yr
        ORDER BY yr ASC
    """, params) # <-- Crucial fix: Added 'params' tokens bounding
    
    line_labels = []
    line_values = []
    for r in cur.fetchall():
        if r["yr"] and r["yr"].isdigit():
            line_labels.append(r["yr"])
            line_values.append(r["total"])

    conn.close()

    return {
        "table": table_rows,
        "pie":   {"labels": pie_labels, "values": pie_values},
        "line":  {"labels": line_labels, "values": line_values},
        "filter_options": _filter_options_cache
    }

