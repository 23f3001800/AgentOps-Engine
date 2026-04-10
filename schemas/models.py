from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class EventType(str, Enum):
    BOOKING_CREATED    = "BookingCreated"
    BL_ISSUED          = "BLIssued"
    INVOICE_POSTED     = "InvoicePosted"
    VESSEL_SAILED      = "VesselSailed"
    DANGEROUS_GOODS    = "DangerousGoodsDetected"


class AgentDecision(str, Enum):
    APPROVED   = "APPROVED"
    REJECTED   = "REJECTED"
    ESCALATED  = "ESCALATED"
    FLAGGED    = "FLAGGED"


# ── Event Schemas ────────────────────────────────────────

class BookingEvent(BaseModel):
    booking_id:        str
    customer_id:       str
    vessel_id:         str
    commodity:         str
    quantity:          int = Field(ge=1)
    origin_port:       str
    destination_port:  str
    is_dangerous_goods: bool = False
    declared_weight_kg: float = Field(gt=0)
    booking_date:      str


# ── Agent Result ─────────────────────────────────────────

class AgentResult(BaseModel):
    agent_name:   str
    decision:     AgentDecision
    confidence:   float = Field(ge=0.0, le=1.0)
    reason:       str
    actions_taken: List[str] = []
    needs_rollback: bool = False
    escalate:     bool = False


# ── Screen Manager Output ────────────────────────────────

class ScreenManagerResult(BaseModel):
    event_type:   EventType
    booking_id:   str
    overall_decision: AgentDecision
    agent_results: List[AgentResult]
    latency_ms:   float
    audit_id:     str
    timestamp:    str
    graph_context: Optional[Dict[str, Any]] = None


# ── Audit Log Entry ───────────────────────────────────────

class AuditEntry(BaseModel):
    audit_id:     str
    event_type:   str
    booking_id:   str
    timestamp:    str
    decision:     str
    agents_fired: List[str]
    latency_ms:   float
    needs_rollback: bool
    details:      Dict[str, Any]


# ── API Models ────────────────────────────────────────────

class SimulateRequest(BaseModel):
    event_type: EventType = EventType.BOOKING_CREATED
    booking: BookingEvent


class SimulateResponse(BaseModel):
    result: ScreenManagerResult
    audit_entry: AuditEntry