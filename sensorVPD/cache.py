import sqlite3
from datetime import datetime, timedelta

DB_FILE = "sensor_cache.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS SensorLog (
    logID INTEGER PRIMARY KEY AUTOINCREMENT,
    sensorID INTEGER,
    datetime TEXT DEFAULT CURRENT_TIMESTAMP,
    temperature REAL,
    humidity REAL,
    windspeed REAL,
    windDirection INTEGER,
    VPD REAL,
    uploaded INTEGER DEFAULT 0
);
"""


def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    try:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
    finally:
        conn.close()


def save_reading(timestamp, temperature, humidity, vpd, windspeed=None, windDirection=None, sensor_id=None):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    try:
        conn.execute(
            "INSERT INTO SensorLog (sensorID, datetime, temperature, humidity, windspeed, windDirection, VPD) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sensor_id, timestamp, temperature, humidity, windspeed, windDirection, vpd)
        )
        conn.commit()
    finally:
        conn.close()


def get_unsent():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT logID AS id, sensorID, datetime AS timestamp, temperature, humidity, windspeed, windDirection, VPD AS vpd FROM SensorLog WHERE uploaded = 0 ORDER BY logID ASC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def mark_uploaded(record_id):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    try:
        conn.execute(
            "UPDATE SensorLog SET uploaded = 1 WHERE logID = ?",
            (record_id,)
        )
        conn.commit()
    finally:
        conn.close()


def cleanup(days=30):
    cutoff = datetime.utcnow() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_FILE, timeout=10)
    try:
        conn.execute(
            "DELETE FROM SensorLog WHERE uploaded = 1 AND datetime < ?",
            (cutoff_str,)
        )
        conn.commit()
    finally:
        conn.close()
