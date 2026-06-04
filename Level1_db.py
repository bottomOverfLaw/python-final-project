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







# ══════════════════════════════════════════
#  ABOUT PAGE
# ══════════════════════════════════════════