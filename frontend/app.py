import streamlit as st
import requests
import json

st.set_page_config(
    page_title="Ops Agent Simulator",
    page_icon="🚢",
    layout="wide",
)

with st.sidebar:
    st.title("⚙️ Settings")
    api_url = st.text_input("FastAPI URL", value="https://agentops-engine.onrender.com")
    if st.button("🔍 Health Check"):
        try:
            r = requests.get(f"{api_url}/health", timeout=5)
            if r.ok:
                d = r.json()
                st.success(f"Online ✅ | Bus: {d['event_bus']} | Graph: {d['graph_store']}")
            else:
                st.error(r.text)
        except Exception as e:
            st.error(f"Unreachable: {e}")

    st.divider()
    st.caption("Agent Hierarchy")
    st.markdown("""
    ```
    BookingCreated Event
          ↓
    Screen Manager
    ┌─────────────────┐
    │ ValidationAgent │
    │ ComplianceAgent │
    │ BillingAgent    │
    │ FollowUpAgent   │
    └─────────────────┘
          ↓
    EscalationAgent (if needed)
          ↓
    Audit Log
    ```
    """)

st.title("🚢 Ops Agent Simulator")
st.caption("Event-driven micro-agent hierarchy · Guardrails · Audit Trail · Graph Context")

tabs = st.tabs(["🚀 Simulate", "📋 Audit Log", "ℹ️ Architecture"])

# ── Tab 1: Simulate ───────────────────────────────────────
with tabs[0]:
    st.subheader("Fire a BookingCreated Event")

    col1, col2 = st.columns(2)
    with col1:
        booking_id        = st.text_input("Booking ID", value="BKG-2026-001")
        customer_id       = st.text_input("Customer ID", value="CUST-NEW-001")
        vessel_id         = st.text_input("Vessel ID", value="VSL-ALPHA-01")
        commodity         = st.text_input("Commodity", value="Electronics")

    with col2:
        quantity          = st.number_input("Quantity (TEUs)", min_value=1, value=10)
        origin_port       = st.text_input("Origin Port", value="SGSIN")
        destination_port  = st.text_input("Destination Port", value="NLRTM")
        declared_weight   = st.number_input("Declared Weight (kg)", min_value=1.0, value=5000.0)
        is_dg             = st.checkbox("Dangerous Goods?")
        booking_date      = st.text_input("Booking Date", value="2026-04-10")

    if st.button("🔥 Fire Event", use_container_width=True):
        payload = {
            "event_type": "BookingCreated",
            "booking": {
                "booking_id":        booking_id,
                "customer_id":       customer_id,
                "vessel_id":         vessel_id,
                "commodity":         commodity,
                "quantity":          quantity,
                "origin_port":       origin_port,
                "destination_port":  destination_port,
                "is_dangerous_goods": is_dg,
                "declared_weight_kg": declared_weight,
                "booking_date":      booking_date,
            },
        }
        with st.spinner("Running micro-agents in parallel..."):
            try:
                r = requests.post(f"{api_url}/simulate", json=payload, timeout=60)
                if r.ok:
                    data = r.json()
                    result = data["result"]
                    audit  = data["audit_entry"]

                    # Overall decision badge
                    decision = result["overall_decision"]
                    color = {
                        "APPROVED":  "🟢",
                        "REJECTED":  "🔴",
                        "ESCALATED": "🟠",
                        "FLAGGED":   "🟡",
                    }.get(decision, "⚪")

                    st.subheader(f"{color} Overall Decision: {decision}")

                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Latency", f"{result['latency_ms']} ms")
                    col_b.metric("Agents Fired", len(result["agent_results"]))
                    col_c.metric("Audit ID", audit["audit_id"])

                    # Agent results
                    st.divider()
                    st.subheader("Agent Decisions")
                    for ar in result["agent_results"]:
                        badge = {
                            "APPROVED":  "✅",
                            "REJECTED":  "❌",
                            "ESCALATED": "⚠️",
                            "FLAGGED":   "🚩",
                        }.get(ar["decision"], "⚪")
                        with st.expander(f"{badge} {ar['agent_name']} → {ar['decision']}"):
                            st.write(f"**Confidence:** {ar['confidence']:.2f}")
                            st.write(f"**Reason:** {ar['reason']}")
                            if ar["actions_taken"]:
                                st.write("**Actions taken:**")
                                for a in ar["actions_taken"]:
                                    st.write(f"  - {a}")
                            if ar["needs_rollback"]:
                                st.error("⚠️ Rollback required")

                    # Graph context
                    if result.get("graph_context"):
                        with st.expander("🕸️ Graph Context"):
                            st.json(result["graph_context"])

                    # Audit entry
                    with st.expander("📋 Audit Entry"):
                        st.json(audit)

                else:
                    st.error(f"Error: {r.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"API not reachable: {e}")

# ── Tab 2: Audit Log ──────────────────────────────────────
with tabs[1]:
    st.subheader("Audit Log")
    if st.button("🔄 Load Audit Log"):
        try:
            r = requests.get(f"{api_url}/audit/log?limit=20", timeout=10)
            if r.ok:
                data = r.json()
                st.write(f"**{data['total']} entries**")
                for entry in reversed(data["entries"]):
                    badge = "✅" if entry["decision"] == "APPROVED" else (
                            "❌" if entry["decision"] == "REJECTED" else "⚠️"
                    )
                    with st.expander(
                        f"{badge} [{entry['audit_id']}] {entry['event_type']} — "
                        f"Booking {entry['booking_id']} — {entry['decision']}"
                    ):
                        st.write(f"**Timestamp:** {entry['timestamp']}")
                        st.write(f"**Agents:** {', '.join(entry['agents_fired'])}")
                        st.write(f"**Latency:** {entry['latency_ms']} ms")
                        if entry["needs_rollback"]:
                            st.error("Rollback required")
                        st.json(entry["details"])
        except Exception as e:
            st.error(str(e))

# ── Tab 3: Architecture ───────────────────────────────────
with tabs[2]:
    st.subheader("System Architecture")
    st.markdown("""
    ### Agent Hierarchy (3 Levels)
    | Level | Component | Role |
    |---|---|---|
    | L1 | Domain Director | Routes events to correct Screen Manager |
    | L2 | Screen Manager | Orchestrates micro-agents for one event type |
    | L3 | Micro-Agents | Discrete workers: Validation, Compliance, Billing, FollowUp |

    ### Guardrails on Every Agent
    - Input schema validation (Pydantic)
    - Confidence threshold check
    - Human review escalation flag
    - Rollback flag on rejection
    - Audit log for every action

    ### Event-Driven Architecture
    - BookingCreated → Screen Manager → parallel micro-agents
    - In-memory event bus (Redis interface ready)
    - Graph store seeds on every event (Neo4j interface ready)

    ### Graph Context (Neo4j-ready)
    ```cypher
    MATCH (b:Booking {id: $booking_id})-[:FOR_CUSTOMER]->(c:Customer)
    RETURN b, c

    MATCH (b:Booking)-[:ON_VESSEL]->(v:Vessel)
    WHERE b.id = $booking_id
    RETURN v.current_load

    MATCH (c:Customer {id: $customer_id})-[:PLACED]->(b:Booking)
    RETURN count(b) as total_bookings
    ```
    """)
