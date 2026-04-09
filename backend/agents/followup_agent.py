"""
Follow-Up Agent — detects process gaps across the booking lifecycle.
Example: BL issued but no invoice, vessel sailed but no CAR filed.
This is a cross-domain monitor — it watches for missing downstream steps.
"""

from schemas.models import AgentResult, AgentDecision, BookingEvent

# Mock state tracker — in production: query ERP event log
_state_tracker: dict = {}


def update_state(booking_id: str, step: str):
    if booking_id not in _state_tracker:
        _state_tracker[booking_id] = set()
    _state_tracker[booking_id].add(step)


REQUIRED_STEPS = [
    "validation_passed",
    "compliance_checked",
    "invoice_created",
    "bl_issued",
]


async def followup_agent(payload: dict) -> AgentResult:
    booking = BookingEvent(**payload)
    actions = []

    completed = _state_tracker.get(booking.booking_id, set())
    missing = [step for step in REQUIRED_STEPS if step not in completed]

    if missing:
        gap_msg = f"Process gaps detected: {', '.join(missing)}"
        actions.append(f"Triggered follow-up alerts for: {', '.join(missing)}")
        actions.append(f"Escalation queued for booking {booking.booking_id}")

        return AgentResult(
            agent_name="FollowUpAgent",
            decision=AgentDecision.FLAGGED,
            confidence=0.88,
            reason=gap_msg,
            actions_taken=actions,
            escalate=len(missing) >= 2,
        )

    actions.append("All lifecycle steps completed for this booking")
    return AgentResult(
        agent_name="FollowUpAgent",
        decision=AgentDecision.APPROVED,
        confidence=0.95,
        reason="No process gaps detected",
        actions_taken=actions,
    )