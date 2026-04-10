"""
Graph Store — Neo4j abstraction.
Uses Neo4j if USE_NEO4J=true, otherwise in-memory dict graph.
Provides entity relationship context to agents before they act.
"""

from typing import Dict, List, Any, Optional
from config import settings


# ── In-Memory Graph ───────────────────────────────────────

class InMemoryGraph:
    """Mock graph with same interface as Neo4j driver."""

    def __init__(self):
        self._nodes: Dict[str, Dict] = {}
        self._edges: List[Dict] = []

    def upsert_node(self, label: str, node_id: str, props: Dict):
        self._nodes[node_id] = {"label": label, "id": node_id, **props}

    def add_edge(self, from_id: str, to_id: str, rel_type: str, props: Dict = {}):
        self._edges.append({
            "from": from_id,
            "to": to_id,
            "type": rel_type,
            **props,
        })

    def get_booking_context(self, booking_id: str) -> Dict[str, Any]:
        """Return full context for a booking — what agents use to reason."""
        booking = self._nodes.get(booking_id, {})
        related_edges = [e for e in self._edges if e["from"] == booking_id]
        related_nodes = [
            self._nodes.get(e["to"], {})
            for e in related_edges
        ]
        return {
            "booking": booking,
            "relationships": related_edges,
            "related_entities": related_nodes,
        }

    def check_customer_history(self, customer_id: str) -> Dict:
        bookings = [
            n for n in self._nodes.values()
            if n.get("label") == "Booking"
            and n.get("customer_id") == customer_id
        ]
        return {
            "customer_id": customer_id,
            "total_bookings": len(bookings),
            "risk_flag": len(bookings) == 0,
        }

    def get_vessel_load(self, vessel_id: str) -> Dict:
        vessel_bookings = [
            n for n in self._nodes.values()
            if n.get("label") == "Booking"
            and n.get("vessel_id") == vessel_id
        ]
        return {
            "vessel_id": vessel_id,
            "current_bookings": len(vessel_bookings),
            "overloaded": len(vessel_bookings) > 100,
        }


# ── Neo4j Graph ───────────────────────────────────────────

class Neo4jGraph:
    def __init__(self):
        from neo4j import GraphDatabase
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def upsert_node(self, label: str, node_id: str, props: Dict):
        with self._driver.session() as session:
            props["id"] = node_id
            session.run(
                f"MERGE (n:{label} {{id: $id}}) SET n += $props",
                id=node_id, props=props
            )

    def add_edge(self, from_id: str, to_id: str, rel_type: str, props: Dict = {}):
        with self._driver.session() as session:
            session.run(
                f"""
                MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $props
                """,
                from_id=from_id, to_id=to_id, props=props
            )

    def get_booking_context(self, booking_id: str) -> Dict[str, Any]:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (b:Booking {id: $booking_id})
                OPTIONAL MATCH (b)-[r]->(n)
                RETURN b, collect({rel: type(r), node: n}) as related
                """,
                booking_id=booking_id
            )
            record = result.single()
            if not record:
                return {}
            return {
                "booking": dict(record["b"]),
                "related": record["related"],
            }

    def check_customer_history(self, customer_id: str) -> Dict:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (c:Customer {id: $customer_id})-[:PLACED]->(b:Booking)
                RETURN count(b) as total
                """,
                customer_id=customer_id
            )
            record = result.single()
            total = record["total"] if record else 0
            return {
                "customer_id": customer_id,
                "total_bookings": total,
                "risk_flag": total == 0,
            }

    def get_vessel_load(self, vessel_id: str) -> Dict:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (v:Vessel {id: $vessel_id})<-[:ON_VESSEL]-(b:Booking)
                RETURN count(b) as current
                """,
                vessel_id=vessel_id
            )
            record = result.single()
            current = record["current"] if record else 0
            return {
                "vessel_id": vessel_id,
                "current_bookings": current,
                "overloaded": current > 100,
            }

    def close(self):
        self._driver.close()


# ── Factory ───────────────────────────────────────────────

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        if settings.use_neo4j:
            try:
                _graph = Neo4jGraph()
                print("Graph store: Neo4j")
            except Exception:
                print("Neo4j unavailable, falling back to in-memory graph")
                _graph = InMemoryGraph()
        else:
            _graph = InMemoryGraph()
            print("Graph store: In-Memory (Neo4j interface)")
    return _graph


def seed_graph(booking_event: Dict):
    """Seed graph with booking entity and relationships."""
    graph = get_graph()

    graph.upsert_node("Booking", booking_event["booking_id"], {
        "customer_id": booking_event["customer_id"],
        "vessel_id":   booking_event["vessel_id"],
        "commodity":   booking_event["commodity"],
        "origin":      booking_event["origin_port"],
        "destination": booking_event["destination_port"],
        "status":      "PENDING",
    })

    graph.upsert_node("Customer", booking_event["customer_id"], {
        "id": booking_event["customer_id"],
    })

    graph.upsert_node("Vessel", booking_event["vessel_id"], {
        "id": booking_event["vessel_id"],
    })

    graph.add_edge(booking_event["booking_id"], booking_event["customer_id"], "FOR_CUSTOMER")
    graph.add_edge(booking_event["booking_id"], booking_event["vessel_id"], "ON_VESSEL")