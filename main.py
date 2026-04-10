import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from schemas.models import SimulateRequest, SimulateResponse, AgentDecision
from core.screen_manager import handle_booking_created
from core.audit_log import create_audit_entry, get_audit_log, get_entry
from core.event_bus import get_event_bus


@asynccontextmanager
async def lifespan(app: FastAPI):
    bus = get_event_bus()
    bus.subscribe("BookingCreated", handle_booking_created)
    print("Ops Agent Simulator ready. Event bus wired.")
    yield
    print("Shutting down.")


app = FastAPI(
    title="Ops Agent Simulator",
    description=(
        "Event-driven micro-agent hierarchy for maritime ERP simulation. "
        "Domain Directors → Screen Managers → Micro-Agents with guardrails and audit trails."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ops-agent-simulator",
        "event_bus": "redis" if __import__("config").settings.use_redis else "in-memory",
        "graph_store": "neo4j" if __import__("config").settings.use_neo4j else "in-memory",
    }


@app.post("/simulate", response_model=SimulateResponse)
async def simulate(request: SimulateRequest):
    """
    Simulate an ERP event — fires all relevant micro-agents,
    merges results, logs to audit trail, and returns full decision.
    """
    payload = request.booking.model_dump()

    try:
        result = await handle_booking_created(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {str(e)}")

    needs_rollback = result.overall_decision == AgentDecision.REJECTED

    audit = create_audit_entry(
        event_type=request.event_type.value,
        booking_id=request.booking.booking_id,
        decision=result.overall_decision.value,
        agents_fired=[r.agent_name for r in result.agent_results],
        latency_ms=result.latency_ms,
        needs_rollback=needs_rollback,
        details={
            "agent_decisions": [
                {"agent": r.agent_name, "decision": r.decision, "reason": r.reason}
                for r in result.agent_results
            ],
            "graph_context": result.graph_context,
        },
    )

    result.audit_id = audit.audit_id
    return SimulateResponse(result=result, audit_entry=audit)


@app.get("/audit/log")
async def audit_log(limit: int = 50):
    """Return recent audit log entries."""
    entries = get_audit_log(limit)
    return {
        "total": len(entries),
        "entries": [e.model_dump() for e in entries],
    }


@app.get("/audit/{audit_id}")
async def audit_detail(audit_id: str):
    entry = get_entry(audit_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found.")
    return entry


@app.get("/events/history")
async def event_history():
    bus = get_event_bus()
    return {"events": bus.get_history()}