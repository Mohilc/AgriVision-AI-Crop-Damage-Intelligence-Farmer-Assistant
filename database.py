"""
AgriVision - Database Module
Handles SQLite persistence for crop damage analyses, chat follow-ups, and aggregate statistics.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "agrivision.db")
UPLOADS_DIR = os.path.join(DB_DIR, "uploads")

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)


def get_db_connection():
    """Returns a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the database schema if tables do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Main analyses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id TEXT,
                telegram_chat_id TEXT,
                username TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                image_path TEXT NOT NULL,
                crop_identified TEXT,
                damage_detected BOOLEAN,
                possible_damage_types TEXT,
                possible_cause TEXT,
                severity TEXT,
                estimated_visible_damage_percentage TEXT,
                affected_regions TEXT,
                visible_symptoms TEXT,
                confidence TEXT,
                recommended_next_steps TEXT,
                limitations TEXT,
                raw_json_response TEXT,
                source TEXT DEFAULT 'telegram'
            )
        """)
        
        # Follow-up conversational messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER,
                telegram_user_id TEXT,
                role TEXT NOT NULL,
                message_text TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()


def save_analysis(
    data: Dict[str, Any],
    image_path: str,
    telegram_user_id: Optional[str] = None,
    telegram_chat_id: Optional[str] = None,
    username: Optional[str] = None,
    source: str = "telegram"
) -> int:
    """
    Saves an AI analysis result to the database.
    Returns the newly inserted analysis ID.
    """
    init_db()
    
    # Serialize list fields safely
    possible_damage_types = json.dumps(data.get("possible_damage_types", []))
    affected_regions = json.dumps(data.get("affected_regions", []))
    visible_symptoms = json.dumps(data.get("visible_symptoms", []))
    recommended_next_steps = json.dumps(data.get("recommended_next_steps", []))
    limitations = json.dumps(data.get("limitations", []))
    raw_json = json.dumps(data)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO analyses (
                telegram_user_id,
                telegram_chat_id,
                username,
                timestamp,
                image_path,
                crop_identified,
                damage_detected,
                possible_damage_types,
                possible_cause,
                severity,
                estimated_visible_damage_percentage,
                affected_regions,
                visible_symptoms,
                confidence,
                recommended_next_steps,
                limitations,
                raw_json_response,
                source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(telegram_user_id) if telegram_user_id else None,
            str(telegram_chat_id) if telegram_chat_id else None,
            username,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            image_path,
            data.get("crop_identified", "Unknown"),
            1 if data.get("damage_detected", False) else 0,
            possible_damage_types,
            data.get("possible_cause", "Uncertain"),
            data.get("severity", "None"),
            data.get("estimated_visible_damage_percentage", "Not estimated"),
            affected_regions,
            visible_symptoms,
            data.get("confidence", "Medium"),
            recommended_next_steps,
            limitations,
            raw_json,
            source
        ))
        conn.commit()
        return cursor.lastrowid


def get_analysis_by_id(analysis_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single analysis by its database ID."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        result = dict(row)
        # Parse JSON fields
        for field in ["possible_damage_types", "affected_regions", "visible_symptoms", "recommended_next_steps", "limitations"]:
            if result.get(field):
                try:
                    result[field] = json.loads(result[field])
                except Exception:
                    result[field] = []
        return result


def get_latest_analysis_for_user(telegram_user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the most recent analysis for a given Telegram user."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM analyses WHERE telegram_user_id = ? ORDER BY id DESC LIMIT 1",
            (str(telegram_user_id),)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        result = dict(row)
        for field in ["possible_damage_types", "affected_regions", "visible_symptoms", "recommended_next_steps", "limitations"]:
            if result.get(field):
                try:
                    result[field] = json.loads(result[field])
                except Exception:
                    result[field] = []
        return result


def get_user_history(telegram_user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieves recent history for a given Telegram user."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, crop_identified, severity, estimated_visible_damage_percentage, timestamp, possible_cause "
            "FROM analyses WHERE telegram_user_id = ? ORDER BY id DESC LIMIT ?",
            (str(telegram_user_id), limit)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_all_analyses(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves all analyses for dashboard consumption."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            for field in ["possible_damage_types", "affected_regions", "visible_symptoms", "recommended_next_steps", "limitations"]:
                if d.get(field):
                    try:
                        d[field] = json.loads(d[field])
                    except Exception:
                        d[field] = []
            results.append(d)
        return results


def save_chat_message(analysis_id: Optional[int], telegram_user_id: str, role: str, message_text: str):
    """Saves a conversational follow-up message to the database."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_messages (analysis_id, telegram_user_id, role, message_text, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            analysis_id,
            str(telegram_user_id),
            role,
            message_text,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()


def get_chat_history_for_analysis(analysis_id: int, limit: int = 10) -> List[Dict[str, str]]:
    """Retrieves chat messages associated with a specific analysis for context."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, message_text FROM chat_messages
            WHERE analysis_id = ?
            ORDER BY id ASC LIMIT ?
        """, (analysis_id, limit))
        rows = cursor.fetchall()
        return [{"role": r["role"], "content": r["message_text"]} for r in rows]


def get_dashboard_metrics() -> Dict[str, Any]:
    """Computes summary statistics for the Streamlit dashboard."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Total analyses
        cursor.execute("SELECT COUNT(*) FROM analyses")
        total_analyses = cursor.fetchone()[0]
        
        # Total damage detected cases
        cursor.execute("SELECT COUNT(*) FROM analyses WHERE damage_detected = 1")
        total_damaged = cursor.fetchone()[0]
        
        # Unique crops count
        cursor.execute("SELECT COUNT(DISTINCT crop_identified) FROM analyses WHERE crop_identified != 'Unknown' AND crop_identified IS NOT NULL")
        unique_crops = cursor.fetchone()[0]
        
        # Severity breakdown
        cursor.execute("SELECT severity, COUNT(*) as count FROM analyses GROUP BY severity")
        severity_dist = {row["severity"]: row["count"] for row in cursor.fetchall()}
        
        # Top crops analyzed
        cursor.execute("SELECT crop_identified, COUNT(*) as count FROM analyses GROUP BY crop_identified ORDER BY count DESC LIMIT 5")
        top_crops = [{"crop": row["crop_identified"], "count": row["count"]} for row in cursor.fetchall()]
        
        return {
            "total_analyses": total_analyses,
            "total_damaged": total_damaged,
            "unique_crops": unique_crops,
            "severity_distribution": severity_dist,
            "top_crops": top_crops
        }
