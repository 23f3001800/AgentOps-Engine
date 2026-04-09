"""
Compliance Agent — checks dangerous goods, sanctions, port restrictions.
Level 3 micro-agent. Runs after validation.
"""

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from schemas.models import AgentResult, AgentDecision, BookingEvent
from config import settings

# High-risk commodities list
HIGH_RISK_COMMODITIES = [
    "explosives", "radioactive", "toxic", "flammable",
    "corrosive", "oxidizing", "infectious", "gas",
    "ammunition", "weapons", "chemicals",
]

SANCTIONED_PORTS = ["KPNAM", "IRTHB", "SYALA"]  # Mock sanctioned ports

COMPLIANCE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a maritime compliance officer. Assess if a booking has compliance risks.
Check:
1. Is the commodity dangerous or regulated?
2. Are there port restrictions?
3. Is documentation likely required?

Answer ONLY with:
RISK_LEVEL: [LOW/MEDIUM/HIGH]
REASON: [one line]
DOCS_REQUIRED: [yes/no]
""",
    ),
    (
        "human",
        "Booking: {booking_id}\nCommodity: {commodity}\nOrigin: {origin}\nDestination: {destination}\nDangerous goods flag: {is_dg}",
    ),
])


def _llm():
    return ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=0.0,
    )


async def compliance_agent(payload: dict) -> AgentResult:
    booking = BookingEvent(**payload)
    actions = []
    issues = []

    # Rule-based checks (fast, deterministic)
    commodity_lower = booking.commodity.lower()
    is_high_risk = any(h in commodity_lower for h in HIGH_RISK_COMMODITIES)

    if booking.is_dangerous_goods:
        issues.append("Dangerous goods flag set — DG documentation required")
        actions.append("Flagged for DG documentation review")

    if is_high_risk:
        issues.append(f"Commodity '{booking.commodity}' classified as high-risk")
        actions.append("Triggered commodity risk check")

    if booking.origin_port in SANCTIONED_PORTS:
        issues.append(f"Origin port {booking.origin_port} is sanctioned")
        actions.append("Rejected — sanctioned origin port")
        return AgentResult(
            agent_name="ComplianceAgent",
            decision=AgentDecision.REJECTED,
            confidence=0.99,
            reason=f"Sanctioned port: {booking.origin_port}",
            actions_taken=actions,
            escalate=True,
        )

    if booking.destination_port in SANCTIONED_PORTS:
        issues.append(f"Destination port {booking.destination_port} is sanctioned")
        actions.append("Rejected — sanctioned destination port")
        return AgentResult(
            agent_name="ComplianceAgent",
            decision=AgentDecision.REJECTED,
            confidence=0.99,
            reason=f"Sanctioned port: {booking.destination_port}",
            actions_taken=actions,
            escalate=True,
        )

    # LLM-based compliance assessment for edge cases
    if is_high_risk or booking.is_dangerous_goods:
        try:
            chain = COMPLIANCE_PROMPT | _llm() | StrOutputParser()
            llm_result = chain.invoke({
                "booking_id": booking.booking_id,
                "commodity": booking.commodity,
                "origin": booking.origin_port,
                "destination": booking.destination_port,
                "is_dg": booking.is_dangerous_goods,
            })

            if "HIGH" in llm_result:
                actions.append("LLM compliance check: HIGH risk — escalating")
                return AgentResult(
                    agent_name="ComplianceAgent",
                    decision=AgentDecision.ESCALATED,
                    confidence=0.85,
                    reason=f"LLM compliance assessment: {llm_result}",
                    actions_taken=actions,
                    escalate=True,
                )
        except Exception as e:
            issues.append(f"LLM compliance check failed: {e}")

    if issues:
        return AgentResult(
            agent_name="ComplianceAgent",
            decision=AgentDecision.FLAGGED,
            confidence=0.80,
            reason=" | ".join(issues),
            actions_taken=actions,
            escalate=False,
        )

    actions.append("Compliance check passed")
    return AgentResult(
        agent_name="ComplianceAgent",
        decision=AgentDecision.APPROVED,
        confidence=0.95,
        reason="No compliance issues detected",
        actions_taken=actions,
    )