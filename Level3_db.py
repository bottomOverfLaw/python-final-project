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
    Injury rate by age group × person type × speed zone.
    filters: dict with optional keys level, age, light
    """
    filters = filters or {}
    where_clauses = [
        "p.INJ_LEVEL IS NOT NULL",
        "a.SPEED_ZONE NOT IN (0, 777, 888, 999)"
    ]
    params = []

    if filters.get("level"):
        ph = ",".join("?" * len(filters["level"]))
        where_clauses.append(f"p.INJ_LEVEL IN ({ph})")
        params += [int(v) for v in filters["level"]]

    if filters.get("age"):
        ph = ",".join("?" * len(filters["age"]))
        where_clauses.append(f"p.AGE_GROUP IN ({ph})")
        params += list(filters["age"])

    if filters.get("light"):
        ph = ",".join("?" * len(filters["light"]))
        where_clauses.append(f"a.LIGHT_CONDITION IN ({ph})")
        params += [int(v) for v in filters["light"]]

    where = "WHERE " + " AND ".join(where_clauses)

    rows = query(f"""
        SELECT
            CASE WHEN p.AGE_GROUP = '5-Dec' THEN '5-12' ELSE p.AGE_GROUP END AS age,
            ru.ROAD_USER_TYPE_DESC AS person_type,
            a.SPEED_ZONE AS speed_zone,
            ROUND(100.0 * SUM(CASE WHEN p.INJ_LEVEL = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS injury_rate,
            COUNT(*) AS total
        FROM Person p
        JOIN Accident a   ON p.ACCIDENT_NO   = a.ACCIDENT_NO
        JOIN Road_User ru ON p.ROAD_USER_TYPE = ru.ROAD_USER_TYPE
        {where}
        GROUP BY p.AGE_GROUP, p.ROAD_USER_TYPE, a.SPEED_ZONE
        HAVING total > 50
        ORDER BY injury_rate DESC
        LIMIT 20
    """, params)

    if rows:
        avg = sum(r["injury_rate"] for r in rows) / len(rows)
        for r in rows:
            diff = round(r["injury_rate"] - avg, 1)
            r["above"]       = f"+{diff}pp" if diff >= 0 else f"{diff}pp"
            r["above_class"] = "positive" if diff >= 0 else "negative"

    return rows


def people_analysis_chart(filters=None):
    """
    Aggregated injury rate per age group for the bar chart.
    Returns one row per age group for a cleaner chart view.
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

    if filters.get("light"):
        ph = ",".join("?" * len(filters["light"]))
        where_clauses.append(f"a.LIGHT_CONDITION IN ({ph})")
        params += [int(v) for v in filters["light"]]

    where = "WHERE " + " AND ".join(where_clauses)

    return query(f"""
        SELECT
            CASE WHEN p.AGE_GROUP = '5-Dec' THEN '5-12' ELSE p.AGE_GROUP END AS age,     
            ROUND(100.0 * SUM(CASE WHEN p.INJ_LEVEL = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS injury_rate
        FROM Person p
        JOIN Accident a ON p.ACCIDENT_NO = a.ACCIDENT_NO
        {where}
        GROUP BY p.AGE_GROUP
        ORDER BY injury_rate DESC
    """, params)


# ══════════════════════════════════════════
#  ACCIDENT ANALYSIS PAGE
# ══════════════════════════════════════════
def get_accident_analysis(postcode=None, light=None, atmo=None, road=None):
    """
    Table + chart data for accident analysis page.
    Only joins Node table when postcode filter is needed.
    """
    where_clauses = ["1=1"]
    params = []
    node_join = ""


    if postcode:
        node_join = "JOIN Node n ON a.NODE_ID = n.NODE_ID"
        where_clauses.append("n.POSTCODE = ?")
        params.append(int(postcode))

    if light:
        ph = ",".join("?" * len(light))
        where_clauses.append(f"lc.COND_NAME IN ({ph})")
        params += light

    where = "WHERE " + " AND ".join(where_clauses)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(f"""
        SELECT
            a.ACCIDENT_NO,
            lc.COND_NAME        AS light,
            a.ROAD_TYPE         AS road_type,
            a.ROAD_NAME_INT     AS intersection,
            a.NO_PERSONS        AS people,
            a.ACCIDENT_DATE     AS date,
            a.ACCIDENT_TIME     AS time,
            SUBSTR(a.ACCIDENT_DATE, -4, 4) AS year,
            (SELECT ac.ATMOSPH_COND_DESC
             FROM Atmospheric_Cond_Seq acs
             JOIN Amospheric_Cond ac ON acs.ATMOSPH_COND = ac.ATMOSPH_COND
             WHERE acs.ACCIDENT_NO = a.ACCIDENT_NO
             AND acs.ATMOSPH_COND_SEQ = 1
             LIMIT 1) AS atmo
        FROM Accident a
        {node_join}
        JOIN Light_Condition lc ON a.LIGHT_CONDITION = lc.COND_ID
        {where}
        ORDER BY a.ACCIDENT_DATE DESC
        LIMIT 200
    """, params)
    rows = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT DISTINCT COND_NAME FROM Light_Condition ORDER BY COND_NAME")
    light_opts = [r["COND_NAME"] for r in cur.fetchall()]

    cur.execute("SELECT DISTINCT SURFACE_COND_DESC FROM Road_Surface_Cond ORDER BY SURFACE_COND_DESC")
    road_opts = [r["SURFACE_COND_DESC"] for r in cur.fetchall()]

    cur.execute("SELECT DISTINCT ATMOSPH_COND_DESC FROM Amospheric_Cond ORDER BY ATMOSPH_COND_DESC")
    atmo_opts = [r["ATMOSPH_COND_DESC"] for r in cur.fetchall()]

    conn.close()

    for i, r in enumerate(rows):
        r["serial"] = i + 1
        r["road"]   = r.get("road_type") or "—"
        if not r.get("atmo"):
            r["atmo"] = "—"

    road_type_counts = {}
    for r in rows:
        rt = r["road_type"] or "Unknown"
        road_type_counts[rt] = road_type_counts.get(rt, 0) + 1

    year_counts = {}
    for r in rows:
        yr = r["year"] or "Unknown"
        year_counts[yr] = year_counts.get(yr, 0) + 1
    sorted_years = sorted(year_counts.keys())

    return {
        "table": rows,
        "pie": {
            "labels": list(road_type_counts.keys()),
            "values": list(road_type_counts.values()),
        },
        "line": {
            "labels": sorted_years,
            "values": [year_counts[y] for y in sorted_years],
        },
        "filter_options": {
            "light": light_opts,
            "atmo":  atmo_opts,
            "road":  road_opts,
        }
    }