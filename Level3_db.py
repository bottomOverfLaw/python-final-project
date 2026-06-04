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
