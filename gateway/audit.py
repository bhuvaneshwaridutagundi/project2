"""SQLite audit logging for scan metadata."""

import sqlite3
import os
import uuid
from contextlib import closing
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from config import Config


@dataclass
class ScanRecord:
    """Metadata record for a scan operation."""
    scan_id: str
    timestamp: str
    input_type: str  # "text", "file"
    decision: str
    risk_score: int
    finding_codes: str  # comma-separated
    duration_ms: float
    llm_invoked: bool
    file_extension: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class AuditLogger:
    """SQLite-based audit logger for scan operations."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self._db_path = self.config.DATABASE_PATH
        self._use_uri = self._db_path == ":memory:"
        self._keeper_connection = None
        if self._use_uri:
            self._db_path = (
                f"file:gateway_{uuid.uuid4().hex}?mode=memory&cache=shared"
            )
            self._keeper_connection = sqlite3.connect(
                self._db_path, timeout=5.0, uri=True
            )
        self._ensure_db_directory()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a new, thread-safe connection for the current operation."""
        return sqlite3.connect(
            self._db_path, timeout=5.0, uri=self._use_uri
        )

    def _ensure_db_directory(self):
        """Ensure database directory exists."""
        db_dir = os.path.dirname(self._db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _init_db(self):
        """Initialize database schema."""
        with closing(self._get_connection()) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    input_type TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    finding_codes TEXT,
                    duration_ms REAL NOT NULL,
                    llm_invoked INTEGER NOT NULL,
                    file_extension TEXT,
                    error TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def log(
        self,
        scan_id: str,
        input_type: str,
        decision: str,
        risk_score: int,
        finding_codes: List[str],
        duration_ms: float,
        llm_invoked: bool,
        file_extension: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log a scan operation."""
        record = ScanRecord(
            scan_id=scan_id,
            timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            input_type=input_type,
            decision=decision,
            risk_score=risk_score,
            finding_codes=",".join(finding_codes) if finding_codes else "",
            duration_ms=duration_ms,
            llm_invoked=llm_invoked,
            file_extension=file_extension,
            error=error,
        )

        with closing(self._get_connection()) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO scans
                (scan_id, timestamp, input_type, decision, risk_score, finding_codes,
                 duration_ms, llm_invoked, file_extension, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.scan_id,
                record.timestamp,
                record.input_type,
                record.decision,
                record.risk_score,
                record.finding_codes,
                record.duration_ms,
                1 if record.llm_invoked else 0,
                record.file_extension,
                record.error,
            ))
            conn.commit()

    def get_recent_scans(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent scan records (without full content)."""
        with closing(self._get_connection()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM scans
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Return aggregate scan metrics and the last seven days of activity."""
        with closing(self._get_connection()) as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS total_scans,
                    SUM(CASE WHEN decision = 'ALLOW' THEN 1 ELSE 0 END) AS allowed,
                    SUM(CASE WHEN decision = 'FLAG' THEN 1 ELSE 0 END) AS flagged,
                    SUM(CASE WHEN decision IN ('FLAG', 'BLOCK') THEN 1 ELSE 0 END) AS threats,
                    SUM(CASE WHEN decision = 'BLOCK' THEN 1 ELSE 0 END) AS blocked,
                    SUM(CASE WHEN risk_score BETWEEN 0 AND 29 THEN 1 ELSE 0 END) AS low_risk,
                    SUM(CASE WHEN risk_score BETWEEN 30 AND 69 THEN 1 ELSE 0 END) AS medium_risk,
                    SUM(CASE WHEN risk_score BETWEEN 70 AND 100 THEN 1 ELSE 0 END) AS high_risk
                FROM scans
            """).fetchone()
            activity_rows = conn.execute("""
                SELECT date(timestamp) AS scan_date, COUNT(*) AS scans
                FROM scans
                WHERE date(timestamp) >= date('now', '-6 days')
                GROUP BY date(timestamp)
                ORDER BY scan_date
            """).fetchall()

        return {
            "total_scans": row[0] or 0,
            "safe_prompts": row[1] or 0,
            "threats_detected": row[3] or 0,
            "blocked_prompts": row[4] or 0,
            "decisions": {
                "ALLOW": row[1] or 0,
                "FLAG": row[2] or 0,
                "BLOCK": row[4] or 0,
            },
            "risk_distribution": {
                "low": row[5] or 0,
                "medium": row[6] or 0,
                "high": row[7] or 0,
            },
            "activity": [
                {"date": activity_row[0], "scans": activity_row[1]}
                for activity_row in activity_rows
            ],
        }

    def clear_all(self) -> None:
        """Clear all scan records (for testing only)."""
        with closing(self._get_connection()) as conn:
            conn.execute("DELETE FROM scans")
            conn.commit()