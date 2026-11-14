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

    def clear_all(self) -> None:
        """Clear all scan records (for testing only)."""
        with closing(self._get_connection()) as conn:
            conn.execute("DELETE FROM scans")
            conn.commit()