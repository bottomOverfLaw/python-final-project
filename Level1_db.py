"""
db_level1.py — Level 1 queries (People & Injury + Accident Condition pages)
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
#  HOME PAGE
# ══════════════════════════════════════════
def get_home_stats():
    """Summary stats for the home page cards."""
    total = query("SELECT COUNT(*) as total FROM Accident")[0]["total"]
    killed = query("SELECT SUM(NO_PERSONS_KILLED) as total FROM Accident")[0]["total"]
    serious = query("SELECT SUM(NO_PERSONS_INJ_SERIOUS) as total FROM Accident")[0]["total"]
    postcodes = query("SELECT COUNT(DISTINCT POSTCODE) as total FROM Node")[0]["total"]

    # Accidents by postcode — bar chart
    by_postcode = query("""
        SELECT n.POSTCODE, COUNT(a.ACCIDENT_NO) as accident_count
        FROM Accident a
        JOIN Node n ON a.NODE_ID = n.NODE_ID
        WHERE n.POSTCODE IS NOT NULL
        GROUP BY n.POSTCODE
        ORDER BY accident_count DESC
        LIMIT 10
    """)

    # Accidents by vehicle type — pie chart
    by_vehicle = query("""
        SELECT vt.VEHICLE_TYPE_DESC as vehicle, COUNT(v.VEHICLE_ID) as count
        FROM Vehicle v
        JOIN Vehicle_Type vt ON v.VEHICLE_TYPE_ID = vt.VEHICLE_TYPE_ID
        GROUP BY vt.VEHICLE_TYPE_DESC
        ORDER BY count DESC
        LIMIT 5
    """)
    total_vehicles = sum(r["count"] for r in by_vehicle)
    for r in by_vehicle:
        r["percentage"] = round(r["count"] / total_vehicles * 100)

    return {
        "stats": {
            "total_accidents": total,
            "total_killed": killed,
            "total_serious": serious,
            "total_postcodes": postcodes,
        },
        "by_postcode": {
            "labels": [str(r["POSTCODE"]) for r in by_postcode],
            "values": [r["accident_count"] for r in by_postcode],
        },
        "by_vehicle": {
            "labels": [r["vehicle"] for r in by_vehicle],
            "values": [r["count"] for r in by_vehicle],
            "percentages": [r["percentage"] for r in by_vehicle],
        }
    }






# ══════════════════════════════════════════
#  ABOUT PAGE
# ══════════════════════════════════════════