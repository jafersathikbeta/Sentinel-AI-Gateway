"""Sentinel validation engine and SQLite audit logger."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .mitre_mapping import match_threat
from .schema import AgentAction

# Persist audit DB next to the project root (parent of core/)
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "sentinel_audit.db"


class SecurityViolationError(Exception):
    """Raised when an AgentAction matches a known dangerous signature."""

    def __init__(self, message: str, threat_intel: Dict[str, Any]):
        super().__init__(message)
        self.threat_intel = threat_intel
        self.message = message


class SentinelEngine:
    """Validates agent actions against MITRE ATLAS / NIST CSF signatures and audits all decisions."""

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    mitre_mapping TEXT
                )
                """
            )
            conn.commit()

    def _log(
        self,
        action: AgentAction,
        status: str,
        mitre_mapping: Optional[Dict[str, Any]] = None,
    ) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        mapping_json = json.dumps(mitre_mapping) if mitre_mapping else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_log
                    (timestamp, agent_id, action_type, target, status, mitre_mapping)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    action.agent_id,
                    action.action_type.value if hasattr(action.action_type, "value") else str(action.action_type),
                    action.target,
                    status,
                    mapping_json,
                ),
            )
            conn.commit()

    def validate_action(self, action: AgentAction) -> Dict[str, Any]:
        """
        Validate an AgentAction.

        Returns a success payload when allowed.
        Raises SecurityViolationError when blocked (after logging BLOCKED).
        """
        threat = match_threat(
            action.action_type.value if hasattr(action.action_type, "value") else str(action.action_type),
            action.target,
        )

        if threat:
            intel = {
                "MITRE_ATLAS": threat["MITRE_ATLAS"],
                "NIST_CSF": threat["NIST_CSF"],
                "description": threat.get("description", "Security policy violation"),
                "matched_target": threat["target"],
                "action_type": threat["action_type"],
            }
            self._log(action, "BLOCKED", intel)
            raise SecurityViolationError(
                f"Action blocked: {intel['description']}",
                threat_intel=intel,
            )

        self._log(action, "ALLOWED", None)
        return {
            "status": "ALLOWED",
            "message": "Action passed Sentinel validation",
            "agent_id": action.agent_id,
            "action_type": action.action_type.value if hasattr(action.action_type, "value") else str(action.action_type),
            "target": action.target,
        }

    def get_metrics(self, recent_limit: int = 10) -> Dict[str, Any]:
        """Return aggregate metrics and the most recent audit rows."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM audit_log").fetchone()["c"]
            blocked = conn.execute(
                "SELECT COUNT(*) AS c FROM audit_log WHERE status = 'BLOCKED'"
            ).fetchone()["c"]
            rows = conn.execute(
                """
                SELECT id, timestamp, agent_id, action_type, target, status, mitre_mapping
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (recent_limit,),
            ).fetchall()

        recent: List[Dict[str, Any]] = []
        for row in rows:
            mapping = None
            if row["mitre_mapping"]:
                try:
                    mapping = json.loads(row["mitre_mapping"])
                except json.JSONDecodeError:
                    mapping = {"raw": row["mitre_mapping"]}
            recent.append(
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "agent_id": row["agent_id"],
                    "action_type": row["action_type"],
                    "target": row["target"],
                    "status": row["status"],
                    "mitre_mapping": mapping,
                }
            )

        block_rate = round((blocked / total) * 100, 2) if total else 0.0
        return {
            "total_processed": total,
            "total_blocked": blocked,
            "block_rate_pct": block_rate,
            "recent_logs": recent,
        }
