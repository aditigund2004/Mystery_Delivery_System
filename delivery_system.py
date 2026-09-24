"""
FastBox Mystery Delivery System
================================

A logistics simulator for a fictional delivery company, FastBox.

Given a set of warehouses, delivery agents, and packages, this module:
  1. Parses the input JSON describing warehouses / agents / packages.
  2. Assigns every package to the delivery agent nearest to that
     package's warehouse (Euclidean distance, using each agent's
     starting position).
  3. Simulates one day of operations: each agent visits its assigned
     warehouses and destinations *in order*, so the distance traveled
     accounts for the agent's real path across the whole day (not just
     warehouse -> destination in isolation).
  4. Produces a report of packages delivered, total distance traveled,
     and "efficiency" (average distance per package -- lower is
     better) for every agent, plus the single best (most efficient)
     agent.
  5. Saves the report as report.json.

Run directly for a demo against data.json:
    python3 delivery_system.py

Or point it at any other input file:
    python3 delivery_system.py --input data/test_case_3.json --output report_3.json

See README.md for the bonus features (delays, ASCII route map, a new
agent joining mid-day, CSV export of the top performer).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from typing import Dict, List, Tuple, Optional

Point = Tuple[float, float]


# ---------------------------------------------------------------------------
# 1. Parsing
# ---------------------------------------------------------------------------

def load_data(path: str) -> dict:
    """Read and parse the input JSON file by hand (no external libs needed).

    Expected shape:
        {
          "warehouses": {"W1": [x, y], ...},
          "agents":     {"A1": [x, y], ...},
          "packages":   [{"id": "P1", "warehouse": "W1", "destination": [x, y]}, ...]
        }
    """
    with open(path, "r") as f:
        raw_text = f.read()
    data = json.loads(raw_text)  # manual parse of the JSON text

    # Basic structural validation so bad input fails loudly and early.
    for key in ("warehouses", "agents", "packages"):
        if key not in data:
            raise ValueError(f"Input JSON is missing required key: '{key}'")

    return data


# ---------------------------------------------------------------------------
# 2. Distance calculation
# ---------------------------------------------------------------------------

def euclidean_distance(p1: Point, p2: Point) -> float:
    """Straight-line distance between two (x, y) points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


# ---------------------------------------------------------------------------
# 3. Assignment: nearest agent (by distance to the package's warehouse)
# ---------------------------------------------------------------------------

def assign_packages(
    warehouses: Dict[str, Point],
    agents: Dict[str, Point],
    packages: List[dict],
) -> Dict[str, List[dict]]:
    """Assign every package to the agent nearest to its warehouse.

    "Nearest" is measured once, from each agent's starting position to
    the package's warehouse -- this mirrors the spec exactly ("Assign
    each package to the nearest agent based on Euclidean distance from
    agent to warehouse"). Packages keep the order they were given in,
    which matters later for simulating each agent's route.
    """
    assignments: Dict[str, List[dict]] = {agent_id: [] for agent_id in agents}

    for package in packages:
        warehouse_id = package["warehouse"]
        if warehouse_id not in warehouses:
            raise ValueError(f"Package {package['id']} references unknown warehouse '{warehouse_id}'")
        warehouse_pos = warehouses[warehouse_id]

        # Find the agent whose starting position is closest to this warehouse.
        nearest_agent = min(
            agents,
            key=lambda agent_id: euclidean_distance(agents[agent_id], warehouse_pos),
        )
        assignments[nearest_agent].append(package)

    return assignments


# ---------------------------------------------------------------------------
# 4. Simulation: agent travels its route for the day
# ---------------------------------------------------------------------------

def simulate_deliveries(
    warehouses: Dict[str, Point],
    agents: Dict[str, Point],
    assignments: Dict[str, List[dict]],
    delay_probability: float = 0.0,
    max_delay_minutes: float = 0.0,
    rng: Optional[random.Random] = None,
) -> Dict[str, dict]:
    """Simulate each agent's day: pick up at the warehouse, deliver to the
    destination, then move on to the next assigned package -- starting
    each leg from wherever the agent currently is.

    Returns a per-agent dict with packages_delivered, total_distance,
    and (if delay_probability > 0) total_delay_minutes / delayed_packages,
    plus the full ordered route taken (used by the ASCII visualizer).
    """
    rng = rng or random.Random()
    results: Dict[str, dict] = {}

    for agent_id, assigned_packages in assignments.items():
        current_pos = agents[agent_id]
        total_distance = 0.0
        total_delay = 0.0
        delayed_packages = 0
        route: List[Point] = [current_pos]
        delivered = []

        for package in assigned_packages:
            warehouse_pos = warehouses[package["warehouse"]]
            destination_pos = tuple(package["destination"])

            # Leg 1: travel to the warehouse to pick up the package.
            total_distance += euclidean_distance(current_pos, warehouse_pos)
            current_pos = warehouse_pos
            route.append(current_pos)

            # Leg 2: deliver the package to its destination.
            total_distance += euclidean_distance(current_pos, destination_pos)
            current_pos = destination_pos
            route.append(current_pos)

            # Bonus: random delivery delays (traffic, weather, etc.).
            # Delays cost time, not distance, so they don't affect total_distance.
            if delay_probability > 0 and rng.random() < delay_probability:
                delay = rng.uniform(0, max_delay_minutes)
                total_delay += delay
                delayed_packages += 1

            delivered.append(package["id"])

        packages_delivered = len(delivered)
        efficiency = round(total_distance / packages_delivered, 2) if packages_delivered else 0.0

        results[agent_id] = {
            "packages_delivered": packages_delivered,
            "total_distance": round(total_distance, 2),
            "efficiency": efficiency,
            "delivered_ids": delivered,
            "route": route,
        }
        if delay_probability > 0:
            results[agent_id]["total_delay_minutes"] = round(total_delay, 2)
            results[agent_id]["delayed_packages"] = delayed_packages

    return results


# ---------------------------------------------------------------------------
# 5. Report generation
# ---------------------------------------------------------------------------

def generate_report(sim_results: Dict[str, dict], total_package_count: int) -> dict:
    """Build the final report dict, matching the format requested in the
    assignment, plus a couple of useful extras (delivered_ids, sanity check).

    efficiency = total_distance / packages_delivered (lower = better),
    so the best agent is the one with the *lowest* efficiency among
    agents who actually delivered at least one package.
    """
    report: dict = {}
    delivered_total = 0

    for agent_id, stats in sim_results.items():
        entry = {
            "packages_delivered": stats["packages_delivered"],
            "total_distance": stats["total_distance"],
            "efficiency": stats["efficiency"],
        }
        if "total_delay_minutes" in stats:
            entry["total_delay_minutes"] = stats["total_delay_minutes"]
            entry["delayed_packages"] = stats["delayed_packages"]
        report[agent_id] = entry
        delivered_total += stats["packages_delivered"]

    active_agents = {a: s for a, s in sim_results.items() if s["packages_delivered"] > 0}
    best_agent = min(active_agents, key=lambda a: active_agents[a]["efficiency"]) if active_agents else None
    report["best_agent"] = best_agent

    # Sanity check called out explicitly in the assignment notes.
    if delivered_total != total_package_count:
        report["_warning"] = (
            f"Delivered count ({delivered_total}) does not match "
            f"total packages ({total_package_count})"
        )

    return report


def save_report(report: dict, path: str) -> None:
    """Write the report to disk as pretty-printed JSON."""
    # Route data isn't part of the JSON report (it's for the ASCII map only).
    with open(path, "w") as f:
        json.dump(report, f, indent=2)


# ---------------------------------------------------------------------------
# Bonus: a new agent joining mid-day
# ---------------------------------------------------------------------------

def run_with_midday_agent(
    warehouses: Dict[str, Point],
    agents: Dict[str, Point],
    packages: List[dict],
    new_agent_id: str,
    new_agent_pos: Point,
    join_after_package_index: int,
    delay_probability: float = 0.0,
    max_delay_minutes: float = 0.0,
    rng: Optional[random.Random] = None,
) -> Dict[str, dict]:
    """Simulate a day where `new_agent_id` becomes available partway
    through, i.e. after the first `join_after_package_index` packages
    have already been assigned to the original roster.

    Packages before the split are assigned among the original agents;
    packages from the split onward are assigned among the original
    agents *plus* the new one.
    """
    early_packages = packages[:join_after_package_index]
    late_packages = packages[join_after_package_index:]

    early_assignments = assign_packages(warehouses, agents, early_packages)

    agents_with_new = dict(agents)
    agents_with_new[new_agent_id] = new_agent_pos
    late_assignments = assign_packages(warehouses, agents_with_new, late_packages)

    # Merge the two assignment rounds (order preserved within each round).
    combined: Dict[str, List[dict]] = {a: [] for a in agents_with_new}
    for agent_id, pkgs in early_assignments.items():
        combined[agent_id].extend(pkgs)
    for agent_id, pkgs in late_assignments.items():
        combined[agent_id].extend(pkgs)

    return simulate_deliveries(
        warehouses, agents_with_new, combined,
        delay_probability=delay_probability,
        max_delay_minutes=max_delay_minutes,
        rng=rng,
    )


# ---------------------------------------------------------------------------
# Bonus: ASCII visualization of routes
# ---------------------------------------------------------------------------

def visualize_routes_ascii(
    warehouses: Dict[str, Point],
    sim_results: Dict[str, dict],
    width: int = 60,
    height: int = 25,
) -> str:
    """Render a simple ASCII map: warehouses as 'W', each agent's route
    as its own letter, tracing pickup -> destination hops in order.
    Coordinates are scaled to fit the requested grid size.
    """
    all_points: List[Point] = list(warehouses.values())
    for stats in sim_results.values():
        all_points.extend(stats["route"])

    if not all_points:
        return "(nothing to draw)"

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)

    def to_grid(p: Point) -> Tuple[int, int]:
        gx = int((p[0] - min_x) / span_x * (width - 1))
        gy = int((p[1] - min_y) / span_y * (height - 1))
        return gx, gy

    grid = [[" " for _ in range(width)] for _ in range(height)]

    # Draw warehouses first so agent routes can overwrite the glyph if they
    # pass through, but the legend still explains what's underneath.
    for w_id, pos in warehouses.items():
        gx, gy = to_grid(pos)
        grid[gy][gx] = "W"

    # Use a distinct single-character glyph per agent (numbers avoid
    # collisions when agent ids share the same first letter, e.g. A1/A2/A3).
    glyph_pool = "123456789" + "abcdefghijklmnopqrstuvwxyz"
    agent_glyphs = {
        agent_id: glyph_pool[i % len(glyph_pool)]
        for i, agent_id in enumerate(sim_results)
    }

    for agent_id, stats in sim_results.items():
        glyph = agent_glyphs[agent_id]
        route = stats["route"]
        for j in range(len(route) - 1):
            gx0, gy0 = to_grid(route[j])
            gx1, gy1 = to_grid(route[j + 1])
            # Simple line draw (Bresenham-ish) between consecutive stops.
            steps = max(abs(gx1 - gx0), abs(gy1 - gy0), 1)
            for s in range(steps + 1):
                t = s / steps
                gx = round(gx0 + (gx1 - gx0) * t)
                gy = round(gy0 + (gy1 - gy0) * t)
                if grid[gy][gx] == " ":
                    grid[gy][gx] = "."
        # Mark the agent's final stop with its glyph.
        if route:
            gx, gy = to_grid(route[-1])
            grid[gy][gx] = glyph

    lines = ["".join(row) for row in grid]
    legend = "Legend: W = warehouse, . = route, letter = agent's final stop  " + \
             ", ".join(f"{g}={a}" for a, g in agent_glyphs.items())
    return "\n".join(lines) + "\n" + legend


# ---------------------------------------------------------------------------
# Bonus: export top performer to CSV
# ---------------------------------------------------------------------------

def export_top_performer_csv(report: dict, path: str) -> Optional[str]:
    """Write the best agent's stats to a CSV file. Returns the agent id,
    or None if there was no best agent (e.g. no packages at all)."""
    best_agent = report.get("best_agent")
    if not best_agent:
        return None

    stats = report[best_agent]
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["agent"] + list(stats.keys()))
        writer.writerow([best_agent] + list(stats.values()))
    return best_agent


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run(
    input_path: str,
    output_path: str = "report.json",
    show_ascii: bool = False,
    delay_probability: float = 0.0,
    max_delay_minutes: float = 30.0,
    new_agent: Optional[str] = None,
    export_csv: Optional[str] = None,
    seed: Optional[int] = None,
) -> dict:
    """Run the full pipeline end to end and return the report dict."""
    data = load_data(input_path)
    warehouses = {k: tuple(v) for k, v in data["warehouses"].items()}
    agents = {k: tuple(v) for k, v in data["agents"].items()}
    packages = data["packages"]

    rng = random.Random(seed) if seed is not None else random.Random()

    if new_agent:
        # Format: "AGENT_ID:x,y:join_after_index"
        agent_id, coords, join_idx = new_agent.split(":")
        x, y = (float(v) for v in coords.split(","))
        sim_results = run_with_midday_agent(
            warehouses, agents, packages,
            new_agent_id=agent_id,
            new_agent_pos=(x, y),
            join_after_package_index=int(join_idx),
            delay_probability=delay_probability,
            max_delay_minutes=max_delay_minutes,
            rng=rng,
        )
    else:
        assignments = assign_packages(warehouses, agents, packages)
        sim_results = simulate_deliveries(
            warehouses, agents, assignments,
            delay_probability=delay_probability,
            max_delay_minutes=max_delay_minutes,
            rng=rng,
        )

    report = generate_report(sim_results, total_package_count=len(packages))
    save_report(report, output_path)

    if export_csv:
        export_top_performer_csv(report, export_csv)

    if show_ascii:
        print(visualize_routes_ascii(warehouses, sim_results))
        print()

    return report


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FastBox Mystery Delivery System simulator")
    parser.add_argument("--input", default="data.json", help="Path to input JSON (default: data.json)")
    parser.add_argument("--output", default="report.json", help="Path to write the report JSON (default: report.json)")
    parser.add_argument("--ascii", action="store_true", help="Print an ASCII visualization of agent routes")
    parser.add_argument("--delays", action="store_true", help="Enable random delivery delays (bonus)")
    parser.add_argument("--delay-prob", type=float, default=0.3, help="Probability a given delivery is delayed (with --delays)")
    parser.add_argument("--max-delay", type=float, default=30.0, help="Max delay in minutes (with --delays)")
    parser.add_argument(
        "--new-agent", default=None,
        help="Simulate a new agent joining mid-day: 'AGENT_ID:x,y:join_after_index'",
    )
    parser.add_argument("--export-csv", default=None, help="Path to export the top performer as CSV")
    parser.add_argument("--seed", type=int, default=None, help="Random seed, for reproducible delay simulation")
    return parser


def main() -> None:
    args = _build_arg_parser().parse_args()
    report = run(
        input_path=args.input,
        output_path=args.output,
        show_ascii=args.ascii,
        delay_probability=args.delay_prob if args.delays else 0.0,
        max_delay_minutes=args.max_delay,
        new_agent=args.new_agent,
        export_csv=args.export_csv,
        seed=args.seed,
    )
    print(json.dumps(report, indent=2))
    print(f"\nReport saved to {args.output}")


if __name__ == "__main__":
    main()
