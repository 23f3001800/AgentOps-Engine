"""
Screen Manager — orchestrates micro-agents for a given event.
Runs agents in parallel, merges results, triggers escalation if needed.
This is the Level 2 coordinator in the 3-level hierarchy.
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import List

from schemas.models import (
    AgentResult, AgentDecision, BookingEvent,
    ScreenManagerResult, EventType,
)
from agents.validation_agent import validation_agent
from agents.compliance_agent import compliance_agent
from agents.billing_agent import billing_agent
from agents.followup_agent import followup_agent
from agents.escalation_agent import escalation_agent
from core.graph_store import get_graph, seed_graph
from config import settings


def _overall_decision(results: List[AgentResult]) -> AgentDecision:
    """Merge agent decisions — most severe wins."""
    if any(r.decision == AgentDecision.REJECTED for r in results):
        return AgentDecision.REJECTED
    if any(r.decision == AgentDecision.ESCALATED for r in results):
        return AgentDecision.ESCALATED
    if any(r.decision == AgentDecision.FLAGGED for r in results):
        return AgentDecision.FLAGGED
    return AgentDecision.APPROVED


async def handle_booking_created(payload: dict) -> ScreenManagerResult:
    start = time.perf_counter()

    # Step 1: Seed graph with entity relationships
    seed_graph(payload)
    graph = get_graph()
    graph_context = graph.get_booking_context(payload["booking_id"])
    customer_ctx = graph.check_customer_history(payload["customer_id"])
    vessel_ctx = graph.get_vessel_load(payload["vessel_id"])

    # Step 2: Run micro-agents in parallel
    results: List[AgentResult] = await asyncio.gather(
        validation_agent(payload),
        compliance_agent(payload),
        billing_agent(payload),
        followup_agent(payload),
        return_exceptions=False,
    )

    # Step 3: Check if escalation needed
    needs_escalation = (
        any(r.escalate for r in results)
        or any(r.confidence < settings.confidence_threshold for r in results)
        or customer_ctx.get("risk_flag")
        or vessel_ctx.get("overloaded")
    )

    if needs_escalation:
        escalation_reason = (
            "New customer (risk flag)" if customer_ctx.get("risk_flag")
            else "Vessel overloaded" if vessel_ctx.get("overloaded")
            else "Agent triggered escalation"
        )
        esc_result = await escalation_agent(
            booking_id=payload["booking_id"],
            trigger_reason=escalation_reason,
            agent_results=results,
        )
        results.append(esc_result)

    overall = _overall_decision(results)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    return ScreenManagerResult(
        event_type=EventType.BOOKING_CREATED,
        booking_id=payload["booking_id"],
        overall_decision=overall,
        agent_results=results,
        latency_ms=latency_ms,
        audit_id=str(uuid.uuid4())[:8],
        timestamp=datetime.utcnow().isoformat(),
        graph_context={
            "booking": graph_context,
            "customer": customer_ctx,
            "vessel": vessel_ctx,
        },
    )