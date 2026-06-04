"""
db_level2.py — Level 2 queries (People & Injury + Accident Condition pages)
Filtered breakdowns: injury outcomes, ejection, road/weather conditions
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
#  PEOPLE & INJURY PAGE
# ══════════════════════════════════════════

def injury_summary(injury_levels=None):
    """
    Stacked bar: count by injury level.
    injury_levels: list of ints e.g. [1, 2, 3]
    """
    where, params = "", ()
    if injury_levels:
        ph = ",".join("?" * len(injury_levels))
        where  = f"WHERE p.INJ_LEVEL IN ({ph})"
        params = tuple(injury_levels)

    return query(f"""
        SELECT i.INJ_LEVEL_DESC AS label, COUNT(*) AS value
        FROM Person p
        JOIN Injury i ON p.INJ_LEVEL = i.INJ_LEVEL
        {where}
        GROUP BY p.INJ_LEVEL
        ORDER BY p.INJ_LEVEL
    """, params)


def pictogram_data(age_groups=None, injury_levels=None):
    """
    Per-age-group % breakdown of fatal/serious/other.
    Returns dict keyed by age group.
    """
    target_ages = age_groups or ["16-17", "18-21", "70+"]
    params = list(target_ages)
    ph     = ",".join("?" * len(target_ages))

    inj_where = ""
    if injury_levels:
        ip = ",".join("?" * len(injury_levels))
        inj_where = f"AND p.INJ_LEVEL IN ({ip})"
        params += list(injury_levels)

    rows = query(f"""
        SELECT 
            CASE WHEN p.AGE_GROUP = '5-Dec' THEN '5-12' ELSE p.AGE_GROUP END AS AGE_GROUP,
            SUM(CASE WHEN p.INJ_LEVEL = 1 THEN 1 ELSE 0 END) AS fatal,
            SUM(CASE WHEN p.INJ_LEVEL = 2 THEN 1 ELSE 0 END) AS serious,
            SUM(CASE WHEN p.INJ_LEVEL = 3 THEN 1 ELSE 0 END) AS other,
            COUNT(*) AS total
        FROM Person p
        WHERE p.AGE_GROUP IN ({ph})
        {inj_where}
        GROUP BY AGE_GROUP
    """, params)

    result = {}
    for r in rows:
        total = r["total"] or 1
        result[r["AGE_GROUP"]] = {
            "fatal":   round(r["fatal"]   / total * 100),
            "serious": round(r["serious"] / total * 100),
            "other":   round(r["other"]   / total * 100),
        }
    return result


def ejected_hospital_table(filters=None):
    """
    Table: ejected × hospital × age group × road user type.
    filters: dict with optional keys ejected, hospital, age_groups, person_types
    """
    filters = filters or {}
    where_clauses = ["p.EJECTED_CODE NOT IN (9)"]
    params = []

    if filters.get("ejected"):
        ejected_map = {"Y": [1, 2], "N": [0]}
        codes = []
        for v in filters["ejected"]:
            codes += ejected_map.get(v, [])
        if codes:
            where_clauses.append(f"p.EJECTED_CODE IN ({','.join('?'*len(codes))})")
            params += codes

    if filters.get("hospital"):
        vals = filters["hospital"]
        where_clauses.append(f"p.TAKEN_HOSPITAL IN ({','.join('?'*len(vals))})")
        params += vals

    if filters.get("age_groups"):
        vals = filters["age_groups"]
        where_clauses.append(f"p.AGE_GROUP IN ({','.join('?'*len(vals))})")
        params += vals

    if filters.get("person_types"):
        vals = filters["person_types"]
        where_clauses.append(f"p.ROAD_USER_TYPE IN ({','.join('?'*len(vals))})")
        params += [int(v) for v in vals]

    where = "WHERE " + " AND ".join(where_clauses)

    return query(f"""
        SELECT
            CASE WHEN p.AGE_GROUP = '5-Dec' THEN '5-12' ELSE p.AGE_GROUP END AS age_group,     
            CASE WHEN p.EJECTED_CODE IN (1,2) THEN 'Yes' ELSE 'No' END AS ejected,
            CASE WHEN p.TAKEN_HOSPITAL = 'Y'  THEN 'Yes' ELSE 'No' END AS taken_hospital,
            ru.ROAD_USER_TYPE_DESC AS person_type,
            COUNT(*) AS total_count,
            ROUND(
                100.0 * SUM(CASE WHEN p.INJ_LEVEL = 1 THEN 1 ELSE 0 END) / COUNT(*), 1
            ) AS pct_fatality
        FROM Person p
        JOIN Road_User ru ON p.ROAD_USER_TYPE = ru.ROAD_USER_TYPE
        {where}
        GROUP BY ejected, taken_hospital, p.AGE_GROUP, p.ROAD_USER_TYPE
        ORDER BY total_count DESC
        LIMIT 50
    """, params)

# ── FILTER OPTIONS ──
def get_age_groups():
    rows = query(
        "SELECT DISTINCT AGE_GROUP FROM Person ORDER BY AGE_GROUP"
    )
    
    # fix typo and define correct order
    age_order = [
        "0-4", "5-12", "13-15", "16-17", "18-21",
        "22-25", "26-29", "30-39", "40-49", "50-59",
        "60-64", "65-69", "70+", "Unknown"
    ]
    
    # replace 5-Dec with 5-12
    ages = ["5-12" if r["AGE_GROUP"] == "5-Dec" else r["AGE_GROUP"] for r in rows]
    
    # sort by the defined order, unknowns go to end
    ages.sort(key=lambda x: age_order.index(x) if x in age_order else 999)
    
    return ages

def get_injury_levels():
    return [{"id": r["INJ_LEVEL"], "label": r["INJ_LEVEL_DESC"]}
            for r in query("SELECT * FROM Injury ORDER BY INJ_LEVEL")]

def get_road_user_types():
    return [{"id": r["ROAD_USER_TYPE"], "label": r["ROAD_USER_TYPE_DESC"]}
            for r in query("SELECT * FROM Road_User ORDER BY ROAD_USER_TYPE")]

def get_light_conditions():
    return [{"id": r["COND_ID"], "label": r["COND_NAME"]}
            for r in query("SELECT * FROM Light_Condition ORDER BY COND_ID")]

# ══════════════════════════════════════════
#  ACCIDENT CONDITION PAGE
# ══════════════════════════════════════════
