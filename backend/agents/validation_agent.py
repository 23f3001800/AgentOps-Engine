"""
Validation Agent — checks field completeness and data integrity.
Level 3 micro-agent. Runs first on every BookingCreated event.
"""

from schemas.models import AgentResult, AgentDecision, BookingEvent


REQUIRED_FIELDS = [
    "booking_id", "customer_id", "vessel_id",
    "commodity", "quantity", "origin_port",
    "destination_port", "declared_weight_kg", "booking_date",
]


async def validation_agent(payload: dict) -> AgentResult:
    booking = BookingEvent(**payload)
    actions = []
    issues = []

    # Field completeness check
    for field in REQUIRED_FIELDS:
        if not getattr(booking, field, None):
            issues.append(f"Missing required field: {field}")

    # Business logic validations
    if booking.quantity <= 0:
        issues.append("Quantity must be greater than 0")

    if booking.declared_weight_kg <= 0:
        issues.append("Declared weight must be greater than 0")

    if booking.origin_port == booking.destination_port:
        issues.append("Origin and destination ports cannot be the same")

    if len(booking.booking_id) < 4:
        issues.append("Booking ID too short — likely invalid")

    if issues:
        actions.append(f"Rejected booking {booking.booking_id} — {len(issues)} validation errors")
        return AgentResult(
            agent_name="ValidationAgent",
            decision=AgentDecision.REJECTED,
            confidence=0.98,
            reason=" | ".join(issues),
            actions_taken=actions,
            needs_rollback=False,
            escalate=False,
        )

    actions.append(f"Booking {booking.booking_id} passed all field validations")
    return AgentResult(
        agent_name="ValidationAgent",
        decision=AgentDecision.APPROVED,
        confidence=0.99,
        reason="All required fields present and valid",
        actions_taken=actions,
    )