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

def injury_by_sex(injury_levels=None):
    """Stacked bar: count by sex and injury level."""
    where, params = "", ()
    if injury_levels:
        ph = ",".join("?" * len(injury_levels))
        where  = f"WHERE p.INJ_LEVEL IN ({ph})"
        params = tuple(injury_levels)

    return query(f"""
        SELECT
            CASE p.SEX
                WHEN 'M' THEN 'Male'
                WHEN 'F' THEN 'Female'
                ELSE 'Unknown'
            END AS sex,
            i.INJ_LEVEL_DESC AS injury_label,
            COUNT(*) AS value
        FROM Person p
        JOIN Injury i ON p.INJ_LEVEL = i.INJ_LEVEL
        {where}
        GROUP BY p.SEX, p.INJ_LEVEL
        ORDER BY p.SEX, p.INJ_LEVEL
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
    
    # query to fill the table, calculating the percentage of the fatality 
    return query(f"""
        SELECT
            CASE WHEN p.AGE_GROUP = '5-Dec' THEN '5-12' ELSE p.AGE_GROUP END AS age_group,     
            CASE WHEN p.EJECTED_CODE IN (1,2) THEN 'Yes' ELSE 'No' END AS ejected,
            CASE WHEN p.TAKEN_HOSPITAL = 'Y'  THEN 'Yes' ELSE 'No' END AS taken_hospital,
            ru.ROAD_USER_TYPE_DESC AS person_type,
            ROUND(
                100.0 * SUM(CASE WHEN p.INJ_LEVEL = 1 THEN 1 ELSE 0 END) / COUNT(*), 1
            ) AS pct_fatality
        FROM Person p
        JOIN Road_User ru ON p.ROAD_USER_TYPE = ru.ROAD_USER_TYPE
        {where}
        GROUP BY ejected, taken_hospital, p.AGE_GROUP, p.ROAD_USER_TYPE
        ORDER BY pct_fatality DESC
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
# Descriptions for each condition type
CONDITION_META = {
    'road': {
        'title':      'Accident by road condition:',
        'col_header': 'Surface Type',
        'descriptions': {
            'Dry':   'Road surface is completely dry with normal grip levels.',
            'Wet':   'Road surface is wet due to rain or water accumulation.',
            'Muddy': 'Road surface covered in mud, significantly reducing traction.',
            'Icy':   'Ice patches on the road surface, greatly reducing grip.',
            'Snowy': 'Road covered in snow, creating hazardous driving conditions.',
        }
    },
    'weather': {
        'title':      'Accident by weather condition:',
        'col_header': 'Weather Condition',
        'descriptions': {
            'Clear':   'Clear sky with good visibility and no precipitation.',
            'Raining': 'Rainfall reducing road grip and driver visibility.',
            'Snowing': 'Snowfall creating slippery conditions and reduced visibility.',
            'Fog':     'Dense fog significantly limiting driver visibility.',
            'Wind':    'Strong winds affecting vehicle control.',
            'Smoke':   'Smoke reducing visibility on the road.',
            'Dust':    'Dust reducing visibility and grip.',
            'Not known': 'Weather conditions were not recorded.',
        }
    },
    'light': {
        'title':      'Accident by light condition:',
        'col_header': 'Light Condition',
        'descriptions': {
            'Day':                    'Full daylight with maximum natural visibility.',
            'Dusk/dawn':              'Transitional lighting at dusk or dawn.',
            'Dark street lights on':  'Darkness with street lighting providing some visibility.',
            'Dark street lights off': 'Darkness with street lights off, minimal visibility.',
            'Dark no street lights':  'Darkness with no street lighting.',
            'Dark street lights unknown': 'Darkness with unknown street lighting status.',
        }
    }
}


def get_accident_conditions(condition, postcode=None):
    meta = CONDITION_META.get(condition)
    if not meta:
        return None

    if condition == 'road':
        if postcode:
            rows = query("""
                SELECT rsc.SURFACE_COND_DESC as label, COUNT(*) as count
                FROM Surface_Cond_Seq scs
                JOIN Road_Surface_Cond rsc ON scs.SURFACE_COND = rsc.SURFACE_COND
                JOIN Accident a ON scs.ACCIDENT_NO = a.ACCIDENT_NO
                JOIN Node n ON a.NODE_ID = n.NODE_ID
                WHERE scs.SURFACE_COND_SEQ = 1 AND n.POSTCODE = ?
                GROUP BY rsc.SURFACE_COND_DESC
                ORDER BY count DESC
            """, [int(postcode)])
        else:
            rows = query("""
                SELECT rsc.SURFACE_COND_DESC as label, COUNT(*) as count
                FROM Surface_Cond_Seq scs
                JOIN Road_Surface_Cond rsc ON scs.SURFACE_COND = rsc.SURFACE_COND
                WHERE scs.SURFACE_COND_SEQ = 1
                GROUP BY rsc.SURFACE_COND_DESC
                ORDER BY count DESC
            """)

    elif condition == 'weather':
        if postcode:
            rows = query("""
                SELECT ac.ATMOSPH_COND_DESC as label, COUNT(*) as count
                FROM Atmospheric_Cond_Seq acs
                JOIN Amospheric_Cond ac ON acs.ATMOSPH_COND = ac.ATMOSPH_COND
                JOIN Accident a ON acs.ACCIDENT_NO = a.ACCIDENT_NO
                JOIN Node n ON a.NODE_ID = n.NODE_ID
                WHERE acs.ATMOSPH_COND_SEQ = 1 AND n.POSTCODE = ?
                GROUP BY ac.ATMOSPH_COND_DESC
                ORDER BY count DESC
            """, [int(postcode)])
        else:
            rows = query("""
                SELECT ac.ATMOSPH_COND_DESC as label, COUNT(*) as count
                FROM Atmospheric_Cond_Seq acs
                JOIN Amospheric_Cond ac ON acs.ATMOSPH_COND = ac.ATMOSPH_COND
                WHERE acs.ATMOSPH_COND_SEQ = 1
                GROUP BY ac.ATMOSPH_COND_DESC
                ORDER BY count DESC
            """)

    elif condition == 'light':
        if postcode:
            rows = query("""
                SELECT lc.COND_NAME as label, COUNT(*) as count
                FROM Accident a
                JOIN Light_Condition lc ON a.LIGHT_CONDITION = lc.COND_ID
                JOIN Node n ON a.NODE_ID = n.NODE_ID
                WHERE n.POSTCODE = ?
                GROUP BY lc.COND_NAME
                ORDER BY count DESC
            """, [int(postcode)])
        else:
            rows = query("""
                SELECT lc.COND_NAME as label, COUNT(*) as count
                FROM Accident a
                JOIN Light_Condition lc ON a.LIGHT_CONDITION = lc.COND_ID
                GROUP BY lc.COND_NAME
                ORDER BY count DESC
            """)
    else:
        rows = []

    descriptions = meta['descriptions']
    table_rows = [
        {
            'label':       r['label'],
            'description': descriptions.get(r['label'], '—'),
            'count':       r['count']
        }
        for r in rows
    ]

    postcode_label = f' — Postcode: {postcode}' if postcode else ' — All Postcodes'

    return {
        'title':      meta['title'] + postcode_label,
        'col_header': meta['col_header'],
        'chart': {
            'labels': [r['label'] for r in rows],
            'values': [r['count'] for r in rows],
        },
        'table': table_rows
    }