"""
Billing Agent — checks if invoice preconditions are met.
Ensures BL issuance does not happen without an invoice stub.
"""

from schemas.models import AgentResult, AgentDecision, BookingEvent

# Mock invoice registry — in production: query ERP DB
_invoice_registry: dict = {}


def register_invoice(booking_id: str, invoice_id: str):
    _invoice_registry[booking_id] = invoice_id


async def billing_agent(payload: dict) -> AgentResult:
    booking = BookingEvent(**payload)
    actions = []

    invoice_id = _invoice_registry.get(booking.booking_id)

    if not invoice_id:
        # Auto-create invoice stub (doer action)
        stub_id = f"INV-{booking.booking_id[:6].upper()}-STUB"
        _invoice_registry[booking.booking_id] = stub_id
        actions.append(f"Created invoice stub: {stub_id}")

        return AgentResult(
            agent_name="BillingAgent",
            decision=AgentDecision.FLAGGED,
            confidence=0.90,
            reason=f"No invoice found — auto-created stub {stub_id}",
            actions_taken=actions,
            needs_rollback=False,
        )

    actions.append(f"Invoice {invoice_id} found for booking {booking.booking_id}")
    return AgentResult(
        agent_name="BillingAgent",
        decision=AgentDecision.APPROVED,
        confidence=0.97,
        reason=f"Invoice {invoice_id} exists",
        actions_taken=actions,
    )