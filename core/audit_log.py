"""
Audit Log — immutable record of every agent action.
Stored in memory + written to JSON file.
In production: replace with PostgreSQL or append-only log.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from schemas.models import AuditEntry

_log: List[AuditEntry] = []
LOG_FILE = Path("../data/audit_log.json")


def create_audit_entry(
    event_type: str,
    booking_id: str,
    decision: str,
    agents_fired: List[str],
    latency_ms: float,
    needs_rollback: bool,
    details: Dict[str, Any],
) -> AuditEntry:
    entry = AuditEntry(
        audit_id=str(uuid.uuid4())[:8],
        event_type=event_type,
        booking_id=booking_id,
        timestamp=datetime.utcnow().isoformat(),
        decision=decision,
        agents_fired=agents_fired,
        latency_ms=latency_ms,
        needs_rollback=needs_rollback,
        details=details,
    )
    _log.append(entry)
    _persist(entry)
    return entry


def _persist(entry: AuditEntry):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE) as f:
                existing = json.load(f)
        except Exception:
            existing = []
    existing.append(entry.model_dump())
    with open(LOG_FILE, "w") as f:
        json.dump(existing, f, indent=2)


def get_audit_log(limit: int = 50) -> List[AuditEntry]:
    return _log[-limit:]


def get_entry(audit_id: str) -> AuditEntry | None:
    return next((e for e in _log if e.audit_id == audit_id), None)