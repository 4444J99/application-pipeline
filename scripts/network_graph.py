#!/usr/bin/env python3
"""Network graph for the application pipeline.

Models professional connections as a graph with path-finding to target
companies. Implements Granovetter's weak-ties theory and LinkedIn's
3-degree horizon for network_proximity scoring.

Theory basis:
- Granovetter (1973): weak ties bridge clusters, provide novel job info
- Rajkumar et al. (2022, Science): moderately weak ties (~10 mutual
  connections, low interaction) maximize job mobility in tech
- Referral decay: 1-hop ~30% hire rate, 2-hop ~3-5x cold, 3-hop ~1.5-2x cold
- Cold application: ~0.66% hire rate (1 in 152)

Storage: signals/network.yaml

Usage:
    python scripts/network_graph.py                     # Dashboard: graph stats, org coverage
    python scripts/network_graph.py --path <org>        # Shortest path(s) to org
    python scripts/network_graph.py --path <org> --all  # All paths to org (max 3 hops)
    python scripts/network_graph.py --score <entry-id>  # Network score for entry
    python scripts/network_graph.py --ingest            # Ingest contacts + outreach into graph
    python scripts/network_graph.py --add-edge --from "Name" --to "Name" --strength <1-10>
    python scripts/network_graph.py --set-org "Name" --org "Company"
    python scripts/network_graph.py --map               # Full network map (text)
    python scripts/network_graph.py --orgs              # Org reachability report
    python scripts/network_graph.py --json              # Machine-readable output
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    SIGNALS_DIR,
    atomic_write,
    load_identity,
)

NETWORK_FILE = SIGNALS_DIR / "network.yaml"

# --- Hop-to-score decay (from research) ---
# 1-hop referral: ~30% hire rate (7-15x cold)
# 2-hop warm intro: ~3-5x cold
# 3-hop chain intro: ~1.5-2x cold
# Cold (no path): ~0.66% hire rate
HOP_SCORE = {
    0: 10,  # You are at the org (internal)
    1: 8,   # Direct connection at org
    2: 6,   # 2-hop (warm intro possible)
    3: 4,   # 3-hop (chain intro, near-cold)
}
COLD_SCORE = 1

# Tie strength thresholds for Granovetter inverted-U
TIE_STRENGTH_LABELS = {
    (1, 2): "dormant",
    (3, 4): "weak",
    (5, 6): "moderate",   # Sweet spot per Rajkumar et al.
    (7, 8): "strong",
    (9, 10): "very_strong",
}

# Interaction recency decay (days)
RECENCY_FRESH = 30
RECENCY_WARM = 90
RECENCY_STALE = 180


# --- Data model ---


def load_network() -> dict:
    """Load the network graph from signals/network.yaml."""
    if not NETWORK_FILE.exists():
        return {"nodes": [], "edges": []}
    with open(NETWORK_FILE) as f:
        data = yaml.safe_load(f) or {}
    return {
        "nodes": data.get("nodes", []),
        "edges": data.get("edges", []),
    }


def save_network(network: dict) -> None:
    """Save network graph atomically."""
    content = yaml.dump(
        network,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    atomic_write(NETWORK_FILE, content)


def find_node(network: dict, name: str) -> dict | None:
    """Find a node by name (case-insensitive)."""
    name_lower = name.lower()
    for node in network["nodes"]:
        if node.get("name", "").lower() == name_lower:
            return node
    return None


def ensure_node(network: dict, name: str, **kwargs) -> dict:
    """Find or create a node. Updates fields if provided."""
    node = find_node(network, name)
    if node is None:
        node = {"name": name, "organization": "", "role": "",
                "channel": "linkedin", "last_interaction": "", "tags": []}
        network["nodes"].append(node)
    for k, v in kwargs.items():
        if v:
            node[k] = v
    return node


def find_edge(network: dict, a: str, b: str) -> dict | None:
    """Find an edge between two nodes (undirected)."""
    a_lower, b_lower = a.lower(), b.lower()
    for edge in network["edges"]:
        names = {edge.get("from", "").lower(), edge.get("to", "").lower()}
        if a_lower in names and b_lower in names:
            return edge
    return None


def add_edge(network: dict, a: str, b: str, strength: int = 3,
             relationship_type: str = "professional", note: str = "") -> dict:
    """Add or update an edge between two nodes."""
    edge = find_edge(network, a, b)
    if edge is None:
        edge = {
            "from": a,
            "to": b,
            "strength": max(1, min(10, strength)),
            "relationship_type": relationship_type,
            "created": date.today().isoformat(),
            "note": note,
        }
        network["edges"].append(edge)
    else:
        edge["strength"] = max(1, min(10, strength))
        if note:
            edge["note"] = note
    return edge


# --- Graph operations ---


def build_adjacency(network: dict) -> dict[str, list[tuple[str, int]]]:
    """Build adjacency list: name -> [(neighbor, strength), ...]."""
    adj: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for edge in network["edges"]:
        a, b = edge["from"], edge["to"]
        s = edge.get("strength", 3)
        adj[a].append((b, s))
        adj[b].append((a, s))
    return adj


def get_org_members(network: dict, org: str) -> list[str]:
    """Get all node names at an organization (case-insensitive)."""
    org_lower = org.lower()
    return [n["name"] for n in network["nodes"]
            if n.get("organization", "").lower() == org_lower]


def shortest_paths(network: dict, source: str, target_org: str,
                   max_hops: int = 3) -> list[list[str]]:
    """BFS to find all shortest paths from source to any node at target_org.

    Returns list of paths (each path is a list of node names).
    Stops at max_hops to respect LinkedIn's 3-degree horizon.
    """
    targets = set(n.lower() for n in get_org_members(network, target_org))
    if not targets:
        return []

    adj = build_adjacency(network)
    source_lower = source.lower()

    # BFS
    queue: deque[list[str]] = deque([[source]])
    visited: set[str] = {source_lower}
    found_paths: list[list[str]] = []
    found_depth: int | None = None

    while queue:
        path = queue.popleft()
        depth = len(path) - 1

        if found_depth is not None and depth > found_depth:
            break
        if depth > max_hops:
            break

        current = path[-1]
        current_lower = current.lower()

        if current_lower in targets and depth > 0:
            found_paths.append(path)
            found_depth = depth
            continue

        for neighbor, _strength in adj.get(current, []):
            neighbor_lower = neighbor.lower()
            if neighbor_lower not in visited:
                visited.add(neighbor_lower)
                queue.append(path + [neighbor])

    return found_paths


def all_paths_to_org(network: dict, source: str, target_org: str,
                     max_hops: int = 3) -> list[list[str]]:
    """DFS to find ALL paths (not just shortest) up to max_hops."""
    targets = set(n.lower() for n in get_org_members(network, target_org))
    if not targets:
        return []

    adj = build_adjacency(network)
    all_found: list[list[str]] = []

    def dfs(current: str, path: list[str], visited: set[str]):
        if len(path) - 1 > max_hops:
            return
        current_lower = current.lower()
        if current_lower in targets and len(path) > 1:
            all_found.append(list(path))
            return  # Don't continue past target

        for neighbor, _strength in adj.get(current, []):
            if neighbor.lower() not in visited:
                visited.add(neighbor.lower())
                path.append(neighbor)
                dfs(neighbor, path, visited)
                path.pop()
                visited.discard(neighbor.lower())

    dfs(source, [source], {source.lower()})
    return sorted(all_found, key=len)


def path_strength(network: dict, path: list[str]) -> float:
    """Compute aggregate tie strength along a path.

    Uses harmonic mean — weakest link dominates but doesn't zero out.
    """
    if len(path) < 2:
        return 10.0
    strengths = []
    for i in range(len(path) - 1):
        edge = find_edge(network, path[i], path[i + 1])
        s = edge.get("strength", 3) if edge else 1
        strengths.append(s)
    if not strengths:
        return 1.0
    # Harmonic mean
    return len(strengths) / sum(1.0 / s for s in strengths)


def score_org_proximity(network: dict, source: str, target_org: str) -> dict:
    """Compute network_proximity score for a target organization.

    Returns dict with score, best_path, hop_count, path_strength,
    insider_density, independent_paths.
    """
    paths = all_paths_to_org(network, source, target_org, max_hops=3)
    members = get_org_members(network, target_org)

    if not paths:
        return {
            "score": COLD_SCORE,
            "hop_count": None,
            "best_path": [],
            "path_strength": 0,
            "insider_density": len(members),
            "independent_paths": 0,
            "label": "cold",
        }

    best = min(paths, key=len)
    hops = len(best) - 1
    base_score = HOP_SCORE.get(hops, COLD_SCORE)

    # Tie strength modifier: strong path boosts by 1, weak path penalizes by 1
    ps = path_strength(network, best)
    if ps >= 7:
        strength_mod = 1
    elif ps <= 3:
        strength_mod = -1
    else:
        strength_mod = 0

    # Path redundancy bonus: multiple independent paths boost by 1
    redundancy_mod = 1 if len(paths) >= 2 else 0

    # Insider density bonus: 3+ contacts at org boost by 1
    density_mod = 1 if len(members) >= 3 else 0

    final = max(1, min(10, base_score + strength_mod + redundancy_mod + density_mod))

    # Label
    if hops == 0:
        label = "internal"
    elif hops == 1:
        label = "direct_connection"
    elif hops == 2:
        label = "warm_intro"
    elif hops == 3:
        label = "chain_intro"
    else:
        label = "cold"

    return {
        "score": final,
        "hop_count": hops,
        "best_path": best,
        "path_strength": round(ps, 1),
        "insider_density": len(members),
        "independent_paths": len(paths),
        "label": label,
    }


# --- Ingest from existing data ---

def ingest_from_contacts_and_outreach(network: dict, me: str | None = None) -> int:
    """Ingest contacts.yaml and outreach-log.yaml into the network graph.

    - Each contact becomes a node
    - Each outreach action creates an edge from 'me' to the contact
    - Pipeline entries' organizations are set on nodes
    - Returns count of new items added
    """
    if me is None:
        me = load_identity()["person"]["short_name"]
    added = 0

    # Ensure self node
    ensure_node(network, me, organization="ORGANVM", role="Principal", degree=0)

    # Ingest contacts.yaml
    contacts_file = SIGNALS_DIR / "contacts.yaml"
    if contacts_file.exists():
        with open(contacts_file) as f:
            cdata = yaml.safe_load(f) or {}
        for contact in cdata.get("contacts", []):
            name = contact.get("name", "")
            if not name:
                continue
            org = contact.get("organization", "")
            role = contact.get("role", "")
            channel = contact.get("channel", "linkedin")
            strength = contact.get("relationship_strength", 3)

            node = ensure_node(network, name, organization=org, role=role, channel=channel)
            if not find_edge(network, me, name):
                add_edge(network, me, name, strength=strength,
                         relationship_type="crm_contact")
                added += 1

            # Set last interaction from most recent
            interactions = contact.get("interactions", [])
            if interactions:
                latest = max(interactions, key=lambda x: x.get("date", ""))
                node["last_interaction"] = latest.get("date", "")

    # Ingest outreach-log.yaml
    outreach_file = SIGNALS_DIR / "outreach-log.yaml"
    if outreach_file.exists():
        with open(outreach_file) as f:
            odata = yaml.safe_load(f) or {}
        for entry in odata.get("entries", []):
            contact_name = entry.get("contact", "")
            if not contact_name:
                continue

            # Resolve org from related_targets
            org = ""
            for target_id in entry.get("related_targets", []):
                for d in ALL_PIPELINE_DIRS:
                    fp = d / f"{target_id}.yaml"
                    if fp.exists():
                        tdata = yaml.safe_load(fp.read_text())
                        org = (tdata.get("target") or {}).get("organization", "")
                        break
                if org:
                    break

            etype = entry.get("type", "connect")
            note = entry.get("note", "")
            entry_date = entry.get("date", "")

            # Map outreach type to tie strength
            strength_map = {
                "post_submission": 2,  # Connection request after applying
                "reconnect": 3,       # Re-engaging expired
                "seed": 2,            # Planting for future
            }
            strength = strength_map.get(etype, 2)

            # Boost if DM was sent or accepted
            if "accepted" in note.lower() or "dm sent" in note.lower():
                strength = max(strength, 4)

            node = ensure_node(network, contact_name, organization=org,
                               channel="linkedin")
            if entry_date:
                node["last_interaction"] = entry_date

            if not find_edge(network, me, contact_name):
                add_edge(network, me, contact_name, strength=strength,
                         relationship_type=etype, note=note)
                added += 1
            else:
                # Update strength if higher
                edge = find_edge(network, me, contact_name)
                if edge and strength > edge.get("strength", 0):
                    edge["strength"] = strength

    return added


# --- Display ---


def display_dashboard(network: dict, as_json: bool = False):
    """Display network graph dashboard."""
    nodes = network["nodes"]
    edges = network["edges"]

    # Org distribution
    orgs: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        org = node.get("organization", "Unknown") or "Unknown"
        orgs[org].append(node["name"])

    # Strength distribution
    strength_dist: dict[str, int] = defaultdict(int)
    for edge in edges:
        s = edge.get("strength", 1)
        for (lo, hi), label in TIE_STRENGTH_LABELS.items():
            if lo <= s <= hi:
                strength_dist[label] += 1
                break

    stats = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "organizations": len(orgs),
        "org_breakdown": {k: len(v) for k, v in sorted(orgs.items())},
        "tie_strength_distribution": dict(strength_dist),
    }

    if as_json:
        print(json.dumps(stats, indent=2))
        return

    print("=" * 60)
    print("NETWORK GRAPH DASHBOARD")
    print("=" * 60)
    print(f"\n  Nodes: {stats['total_nodes']}  |  Edges: {stats['total_edges']}  |  Orgs: {stats['organizations']}")

    print("\n  Tie Strength Distribution:")
    for label in ["dormant", "weak", "moderate", "strong", "very_strong"]:
        count = strength_dist.get(label, 0)
        bar = "█" * count
        print(f"    {label:14s} {bar} ({count})")

    print("\n  Organizations:")
    for org, members in sorted(orgs.items(), key=lambda x: -len(x[1])):
        if org in ("ORGANVM", "Unknown"):
            continue
        names = ", ".join(members[:3])
        more = f" +{len(members) - 3}" if len(members) > 3 else ""
        print(f"    {org:30s} [{len(members)}] {names}{more}")


def display_path(network: dict, source: str, target_org: str, show_all: bool = False):
    """Display path-finding results."""
    result = score_org_proximity(network, source, target_org)

    if result["hop_count"] is None:
        print(f"\n  ❌ No path to {target_org} within 3 hops (cold application)")
        print(f"  Score: {result['score']}/10")
        return

    print(f"\n  {'=' * 50}")
    print(f"  PATH TO: {target_org}")
    print(f"  {'=' * 50}")
    print(f"  Score: {result['score']}/10 ({result['label']})")
    print(f"  Hops: {result['hop_count']}  |  Path Strength: {result['path_strength']}")
    print(f"  Independent Paths: {result['independent_paths']}  |  Insiders: {result['insider_density']}")

    print("\n  Best path:")
    path = result["best_path"]
    for i, name in enumerate(path):
        node = find_node(network, name)
        org = node.get("organization", "") if node else ""
        if i < len(path) - 1:
            edge = find_edge(network, path[i], path[i + 1])
            s = edge.get("strength", "?") if edge else "?"
            print(f"    {name} ({org}) --[{s}]--> ", end="")
        else:
            print(f"    {name} ({org})")

    if show_all:
        paths = all_paths_to_org(network, source, target_org)
        if len(paths) > 1:
            print(f"\n  All paths ({len(paths)}):")
            for p in paths:
                ps = path_strength(network, p)
                chain = " → ".join(p)
                print(f"    [{len(p)-1} hop, str={ps:.1f}] {chain}")


def display_org_reachability(network: dict, source: str):
    """Show reachability report for all orgs in the network."""
    orgs = set()
    for node in network["nodes"]:
        org = node.get("organization", "")
        if org and org != "ORGANVM" and org != "Unknown":
            orgs.add(org)

    print(f"\n  {'=' * 60}")
    print("  ORG REACHABILITY REPORT")
    print(f"  {'=' * 60}")
    print(f"  {'Organization':30s} {'Score':>5s} {'Hops':>5s} {'Paths':>5s} {'Label':>18s}")
    print(f"  {'-' * 65}")

    results = []
    for org in sorted(orgs):
        r = score_org_proximity(network, source, org)
        results.append((org, r))

    results.sort(key=lambda x: -x[1]["score"])

    for org, r in results:
        hops = str(r["hop_count"]) if r["hop_count"] is not None else "∞"
        print(f"  {org:30s} {r['score']:>5d} {hops:>5s} {r['independent_paths']:>5d} {r['label']:>18s}")


def display_map(network: dict, source: str):
    """Display full network map as text tree."""
    adj = build_adjacency(network)

    print(f"\n  {'=' * 50}")
    print(f"  NETWORK MAP (from {source})")
    print(f"  {'=' * 50}")

    visited = set()

    def print_tree(name: str, depth: int, prefix: str = ""):
        if depth > 3 or name.lower() in visited:
            return
        visited.add(name.lower())
        node = find_node(network, name)
        org = f" @ {node['organization']}" if node and node.get("organization") else ""
        print(f"  {prefix}{name}{org}")

        neighbors = adj.get(name, [])
        for i, (neighbor, strength) in enumerate(sorted(neighbors, key=lambda x: -x[1])):
            if neighbor.lower() in visited:
                continue
            is_last = i == len(neighbors) - 1
            branch = "└── " if is_last else "├── "
            next_prefix = prefix + ("    " if is_last else "│   ")
            edge = find_edge(network, name, neighbor)
            s = edge.get("strength", "?") if edge else "?"
            node_n = find_node(network, neighbor)
            org_n = f" @ {node_n['organization']}" if node_n and node_n.get("organization") else ""
            print(f"  {prefix}{branch}[{s}] {neighbor}{org_n}")
            # Recurse into neighbor's connections
            print_tree(neighbor, depth + 1, next_prefix)

    print_tree(source, 0)


def sync_to_contacts(network: dict, me: str | None = None) -> int:
    """Sync network graph nodes into contacts.yaml.

    Creates new contacts for nodes not already in contacts.yaml.
    Does not overwrite existing contacts. Returns count of new contacts added.
    """
    if me is None:
        me = load_identity()["person"]["short_name"]
    contacts_file = SIGNALS_DIR / "contacts.yaml"
    if contacts_file.exists():
        with open(contacts_file) as f:
            cdata = yaml.safe_load(f) or {}
    else:
        cdata = {}

    contacts = cdata.get("contacts", [])
    if not isinstance(contacts, list):
        contacts = []

    existing_names = {c.get("name", "").lower() for c in contacts}
    added = 0

    # Pre-load outreach log once (not per-contact)
    outreach_entries: list[dict] = []
    outreach_file = SIGNALS_DIR / "outreach-log.yaml"
    if outreach_file.exists():
        with open(outreach_file) as f:
            odata = yaml.safe_load(f) or {}
        outreach_entries = odata.get("entries", [])

    for node in network["nodes"]:
        name = node.get("name", "")
        if not name or name.lower() == me.lower():
            continue
        if name.lower() in existing_names:
            continue

        edge = find_edge(network, me, name)
        strength = edge.get("strength", 2) if edge else 2

        contact = {
            "name": name,
            "organization": node.get("organization", ""),
            "role": node.get("role", ""),
            "channel": node.get("channel", "linkedin"),
            "relationship_strength": strength,
            "interactions": [],
            "pipeline_entries": [],
            "tags": [],
            "next_action": "",
            "next_action_date": "",
        }

        # Populate interactions from outreach log
        for entry in outreach_entries:
            if entry.get("contact", "").lower() == name.lower():
                contact["interactions"].append({
                    "date": entry.get("date", ""),
                    "type": entry.get("type", "connect"),
                    "note": entry.get("note", ""),
                })
                for t in entry.get("related_targets", []):
                    if t not in contact["pipeline_entries"]:
                        contact["pipeline_entries"].append(t)

        contacts.append(contact)
        existing_names.add(name.lower())
        added += 1

    cdata["contacts"] = contacts
    content = yaml.dump(
        cdata,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    atomic_write(contacts_file, content)
    return added


# --- CLI ---


def main():
    parser = argparse.ArgumentParser(description="Network graph for the application pipeline")
    parser.add_argument("--path", metavar="ORG", help="Find path(s) to organization")
    parser.add_argument("--all", action="store_true", help="Show all paths (with --path)")
    parser.add_argument("--score", metavar="ENTRY_ID", help="Score network proximity for entry")
    parser.add_argument("--ingest", action="store_true", help="Ingest contacts + outreach into graph")
    parser.add_argument("--add-edge", action="store_true", help="Add edge between two nodes")
    parser.add_argument("--from", dest="edge_from", metavar="NAME", help="Edge source node")
    parser.add_argument("--to", dest="edge_to", metavar="NAME", help="Edge target node")
    parser.add_argument("--strength", type=int, default=3, help="Edge strength (1-10)")
    parser.add_argument("--set-org", metavar="NAME", help="Set organization for a node")
    parser.add_argument("--org", metavar="ORG", help="Organization name (with --set-org)")
    parser.add_argument("--map", action="store_true", help="Full network map")
    parser.add_argument("--orgs", action="store_true", help="Org reachability report")
    parser.add_argument("--sync-contacts", action="store_true",
                        help="Sync network nodes into contacts.yaml (creates missing contacts)")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args()

    network = load_network()
    me = load_identity()["person"]["short_name"]

    if args.ingest:
        added = ingest_from_contacts_and_outreach(network, me)
        save_network(network)
        print(f"Ingested {added} new edges. Graph: {len(network['nodes'])} nodes, {len(network['edges'])} edges.")
        return

    if args.add_edge:
        if not args.edge_from or not args.edge_to:
            print("Error: --add-edge requires --from and --to", file=sys.stderr)
            sys.exit(1)
        ensure_node(network, args.edge_from)
        ensure_node(network, args.edge_to)
        add_edge(network, args.edge_from, args.edge_to, strength=args.strength)
        save_network(network)
        print(f"Edge: {args.edge_from} <--[{args.strength}]--> {args.edge_to}")
        return

    if args.sync_contacts:
        added = sync_to_contacts(network, me)
        print(f"Synced {added} new contacts to contacts.yaml.")
        return

    if args.set_org:
        node = find_node(network, args.set_org)
        if not node:
            print(f"Node not found: {args.set_org}", file=sys.stderr)
            sys.exit(1)
        node["organization"] = args.org or ""
        save_network(network)
        print(f"Set {args.set_org} → {args.org}")
        return

    if args.path:
        display_path(network, me, args.path, show_all=args.all)
        return

    if args.score:
        # Load entry to get org
        entry = None
        for d in ALL_PIPELINE_DIRS:
            fp = d / f"{args.score}.yaml"
            if fp.exists():
                entry = yaml.safe_load(fp.read_text())
                break
        if not entry:
            print(f"Entry not found: {args.score}", file=sys.stderr)
            sys.exit(1)
        org = (entry.get("target") or {}).get("organization", "")
        if not org:
            print(f"No organization in entry: {args.score}", file=sys.stderr)
            sys.exit(1)
        result = score_org_proximity(network, me, org)
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            display_path(network, me, org, show_all=True)
        return

    if args.map:
        display_map(network, me)
        return

    if args.orgs:
        display_org_reachability(network, me)
        return

    # Default: dashboard
    display_dashboard(network, as_json=args.json)


if __name__ == "__main__":
    main()
