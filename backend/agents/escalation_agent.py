"""
Escalation Agent — triggered when confidence is low or a critical issue is found.
Produces a human review packet with full context.
"""

from schemas.models import AgentResult, AgentDecision
from typing import List


async def escalation_agent(
    booking_id: str,
    trigger_reason: str,
    agent_results: List[AgentResult],
) -> AgentResult:

    issues = [r.reason for r in agent_results if r.decision != AgentDecision.APPROVED]
    escalating_agents = [r.agent_name for r in agent_results if r.escalate]

    packet_summary = (
        f"ESCALATION PACKET\n"
        f"Booking: {booking_id}\n"
        f"Trigger: {trigger_reason}\n"
        f"Issues: {' | '.join(issues)}\n"
        f"Agents requesting escalation: {', '.join(escalating_agents)}\n"
        f"Action required: Human operator review before proceeding."
    )

    return AgentResult(
        agent_name="EscalationAgent",
        decision=AgentDecision.ESCALATED,
        confidence=1.0,
        reason=packet_summary,
        actions_taken=[
            "Generated escalation packet",
            "Notified human operator queue",
            f"Booking {booking_id} locked pending review",
        ],
        escalate=False,
    )