from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from .schemas import TransactionEvent


@dataclass(slots=True)
class GraphFeatures:
    neighbor_count: int
    risky_neighbor_count: int
    component_size: int
    community_id: str
    related_nodes: list[int]


class InMemoryGraphState:
    def __init__(self, max_edges: int = 200_000) -> None:
        self.max_edges = max_edges
        self.edges: deque[tuple[int, int, bool]] = deque(maxlen=max_edges)
        self.neighbors: dict[int, set[int]] = defaultdict(set)
        self.risky_nodes: set[int] = set()

    def ingest(self, event: TransactionEvent) -> None:
        src = int(event.src_account)
        dst = int(event.dst_account)
        self.edges.append((src, dst, bool(event.is_scripted_fraud)))
        self.neighbors[src].add(dst)
        self.neighbors[dst].add(src)
        if event.is_scripted_fraud:
            self.risky_nodes.add(src)
            self.risky_nodes.add(dst)

    def features(self, node_id: int, depth: int = 2, limit: int = 80) -> GraphFeatures:
        one_hop = set(self.neighbors.get(node_id, set()))
        frontier = set(one_hop)
        component = {node_id, *one_hop}
        for _ in range(max(depth - 1, 0)):
            next_frontier: set[int] = set()
            for node in frontier:
                next_frontier.update(self.neighbors.get(node, set()))
            next_frontier -= component
            component.update(next_frontier)
            frontier = next_frontier
            if len(component) >= limit:
                break
        related = sorted(component - {node_id})[:limit]
        return GraphFeatures(
            neighbor_count=len(one_hop),
            risky_neighbor_count=len(one_hop & self.risky_nodes),
            component_size=len(component),
            community_id=f"comm-{min(component) if component else node_id}",
            related_nodes=related,
        )
