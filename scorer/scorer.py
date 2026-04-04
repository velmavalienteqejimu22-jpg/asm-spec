"""
ASM Scorer — Service selection engine for Agent Service Manifest.

v0.2: Weighted average scoring (demo-ready)
v1.0: Filter (hard constraints) + TOPSIS (multi-criteria ranking)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────

@dataclass
class ServiceVector:
    """Extracted numeric vector from an ASM manifest for scoring."""
    service_id: str
    display_name: str
    taxonomy: str
    cost_per_unit: float          # representative cost (primary billing dimension)
    quality_score: float          # primary quality metric, normalized to [0, 1]
    latency_seconds: float        # p50 latency in seconds
    uptime: float                 # 0-1
    raw_manifest: dict = field(default_factory=dict, repr=False)


@dataclass
class Constraints:
    """Hard constraints — services that violate any constraint are filtered out."""
    min_quality: float | None = None      # e.g., 0.7
    max_cost: float | None = None         # e.g., 0.10
    max_latency_s: float | None = None    # e.g., 5.0
    min_uptime: float | None = None       # e.g., 0.99
    required_taxonomy: str | None = None  # e.g., "ai.llm.chat"


@dataclass
class Preferences:
    """Soft preferences — weights for scoring dimensions. Must sum to 1."""
    cost: float = 0.4
    quality: float = 0.35
    speed: float = 0.15
    reliability: float = 0.10

    def __post_init__(self):
        total = self.cost + self.quality + self.speed + self.reliability
        if not math.isclose(total, 1.0, abs_tol=0.01):
            raise ValueError(f"Preference weights must sum to 1.0, got {total:.3f}")


@dataclass
class ScoredService:
    """A service with its computed score and breakdown."""
    service: ServiceVector
    total_score: float
    breakdown: dict[str, float]
    rank: int = 0
    reasoning: str = ""


# ──────────────────────────────────────────────
# Manifest Parsing
# ──────────────────────────────────────────────

def _parse_latency(s: str | None) -> float:
    """Parse latency string like '800ms', '3s', '~15s' into seconds."""
    if not s:
        return float("inf")
    s = s.strip().lstrip("~").lstrip("<").lstrip(">")
    if s.endswith("ms"):
        return float(s[:-2]) / 1000
    if s.endswith("s"):
        return float(s[:-1])
    if s.endswith("min"):
        return float(s[:-3]) * 60
    try:
        return float(s)
    except ValueError:
        return float("inf")


def _extract_primary_cost(pricing: dict) -> float:
    """Extract a representative cost from billing_dimensions.
    
    For multi-dimension services (e.g., LLM with input+output tokens),
    uses a weighted estimate: cost = 0.3 * input + 0.7 * output
    (typical chat usage ratio).
    """
    dims = pricing.get("billing_dimensions", [])
    if not dims:
        return 0.0

    # Special handling for LLM input+output token pricing
    input_cost = None
    output_cost = None
    for d in dims:
        dim = d.get("dimension", "")
        cost = d.get("cost_per_unit", 0)
        unit = d.get("unit", "per_1")

        # Normalize to per-unit cost
        if unit == "per_1M":
            cost = cost / 1_000_000
        elif unit == "per_1K":
            cost = cost / 1_000

        if dim == "input_token":
            input_cost = cost
        elif dim == "output_token":
            output_cost = cost

    if input_cost is not None and output_cost is not None:
        # Typical chat ratio: 30% input, 70% output
        return 0.3 * input_cost + 0.7 * output_cost

    # Single dimension — use first
    d = dims[0]
    cost = d.get("cost_per_unit", 0)
    unit = d.get("unit", "per_1")
    if unit == "per_1M":
        cost = cost / 1_000_000
    elif unit == "per_1K":
        cost = cost / 1_000
    return cost


def _extract_primary_quality(quality: dict) -> float:
    """Extract primary quality score, normalized to [0, 1]."""
    metrics = quality.get("metrics", [])
    if not metrics:
        return 0.5  # unknown quality → neutral

    m = metrics[0]
    score = m.get("score", 0)
    scale = m.get("scale", "")

    # Normalize based on scale
    if scale == "Elo":
        # LMSYS Elo: roughly 800-1400 range, map to [0, 1]
        return min(max((score - 800) / 600, 0), 1)
    elif scale == "0-100":
        return score / 100
    elif scale == "0-1":
        return score
    elif scale == "1-5":
        return (score - 1) / 4
    elif scale == "lower_is_better":
        # FID-like metrics: lower is better, map 0→1, 50→0
        return max(1 - score / 50, 0)
    else:
        # Best guess: if score > 1, assume 0-100 or similar
        if score > 1:
            return min(score / 100, 1)
        return score


def parse_manifest(manifest: dict) -> ServiceVector:
    """Parse an ASM manifest JSON into a scoreable ServiceVector."""
    pricing = manifest.get("pricing", {})
    quality = manifest.get("quality", {})
    sla = manifest.get("sla", {})

    return ServiceVector(
        service_id=manifest["service_id"],
        display_name=manifest.get("display_name", manifest["service_id"]),
        taxonomy=manifest["taxonomy"],
        cost_per_unit=_extract_primary_cost(pricing),
        quality_score=_extract_primary_quality(quality),
        latency_seconds=_parse_latency(sla.get("latency_p50")),
        uptime=sla.get("uptime", 0.5),
        raw_manifest=manifest,
    )


# ──────────────────────────────────────────────
# Stage 1: Filter (hard constraints)
# ──────────────────────────────────────────────

def filter_services(
    services: list[ServiceVector],
    constraints: Constraints,
) -> list[ServiceVector]:
    """Filter out services that violate hard constraints."""
    result = []
    for s in services:
        if constraints.required_taxonomy:
            if not s.taxonomy.startswith(constraints.required_taxonomy):
                continue
        if constraints.min_quality is not None and s.quality_score < constraints.min_quality:
            continue
        if constraints.max_cost is not None and s.cost_per_unit > constraints.max_cost:
            continue
        if constraints.max_latency_s is not None and s.latency_seconds > constraints.max_latency_s:
            continue
        if constraints.min_uptime is not None and s.uptime < constraints.min_uptime:
            continue
        result.append(s)
    return result


# ──────────────────────────────────────────────
# Stage 2a: Weighted Average Scorer (v0.2)
# ──────────────────────────────────────────────

def _min_max_normalize(values: list[float], invert: bool = False) -> list[float]:
    """Min-max normalize to [0, 1]. If invert, lower raw = higher normalized."""
    if not values:
        return []
    vmin, vmax = min(values), max(values)
    if vmin == vmax:
        return [1.0] * len(values)
    if invert:
        return [(vmax - v) / (vmax - vmin) for v in values]
    return [(v - vmin) / (vmax - vmin) for v in values]


def score_weighted_average(
    services: list[ServiceVector],
    preferences: Preferences,
) -> list[ScoredService]:
    """Score services using weighted average (ASM v0.2 method)."""
    if not services:
        return []

    costs = [s.cost_per_unit for s in services]
    qualities = [s.quality_score for s in services]
    latencies = [s.latency_seconds for s in services]
    uptimes = [s.uptime for s in services]

    norm_cost = _min_max_normalize(costs, invert=True)       # lower cost → higher score
    norm_quality = _min_max_normalize(qualities, invert=False)  # higher quality → higher score
    norm_speed = _min_max_normalize(latencies, invert=True)     # lower latency → higher score
    norm_uptime = _min_max_normalize(uptimes, invert=False)     # higher uptime → higher score

    results = []
    for i, s in enumerate(services):
        breakdown = {
            "cost": norm_cost[i],
            "quality": norm_quality[i],
            "speed": norm_speed[i],
            "reliability": norm_uptime[i],
        }
        total = (
            preferences.cost * breakdown["cost"]
            + preferences.quality * breakdown["quality"]
            + preferences.speed * breakdown["speed"]
            + preferences.reliability * breakdown["reliability"]
        )
        results.append(ScoredService(
            service=s,
            total_score=round(total, 4),
            breakdown={k: round(v, 4) for k, v in breakdown.items()},
        ))

    results.sort(key=lambda x: x.total_score, reverse=True)
    for i, r in enumerate(results):
        r.rank = i + 1
        r.reasoning = _generate_reasoning(r, preferences)
    return results


def _generate_reasoning(scored: ScoredService, prefs: Preferences) -> str:
    """Generate a human-readable reasoning for the score."""
    s = scored.service
    top_dim = max(scored.breakdown, key=lambda k: getattr(prefs, k) * scored.breakdown[k])
    return (
        f"{s.display_name} scored {scored.total_score:.3f} "
        f"(cost={scored.breakdown['cost']:.2f}, "
        f"quality={scored.breakdown['quality']:.2f}, "
        f"speed={scored.breakdown['speed']:.2f}, "
        f"reliability={scored.breakdown['reliability']:.2f}). "
        f"Strongest weighted dimension: {top_dim}."
    )


# ──────────────────────────────────────────────
# Stage 2b: TOPSIS Scorer (v1.0)
# ──────────────────────────────────────────────

def score_topsis(
    services: list[ServiceVector],
    preferences: Preferences,
) -> list[ScoredService]:
    """Score services using TOPSIS (Technique for Order Preference by
    Similarity to Ideal Solution).

    Steps:
    1. Build decision matrix (m services × 4 criteria)
    2. Normalize using vector normalization
    3. Apply weights
    4. Find positive ideal (A+) and negative ideal (A-) solutions
    5. Calculate distance to A+ and A- for each service
    6. Compute closeness coefficient: C = d- / (d+ + d-)
    7. Rank by C (higher = better)
    """
    if not services:
        return []

    n = len(services)

    # Step 1: Decision matrix — columns: cost(minimize), quality(maximize), speed(minimize latency), reliability(maximize)
    # For TOPSIS, we need to know which criteria are benefit (higher=better) vs cost (lower=better)
    raw = []
    for s in services:
        raw.append([
            s.cost_per_unit,        # cost → minimize
            s.quality_score,        # quality → maximize
            s.latency_seconds,      # latency → minimize
            s.uptime,               # uptime → maximize
        ])

    # Benefit criteria (True = higher is better, False = lower is better)
    is_benefit = [False, True, False, True]
    weights = [preferences.cost, preferences.quality, preferences.speed, preferences.reliability]

    # Step 2: Vector normalization
    num_criteria = 4
    norm = [[0.0] * num_criteria for _ in range(n)]
    for j in range(num_criteria):
        col_sum_sq = math.sqrt(sum(raw[i][j] ** 2 for i in range(n)))
        if col_sum_sq == 0:
            for i in range(n):
                norm[i][j] = 0
        else:
            for i in range(n):
                norm[i][j] = raw[i][j] / col_sum_sq

    # Step 3: Weighted normalized matrix
    weighted = [[norm[i][j] * weights[j] for j in range(num_criteria)] for i in range(n)]

    # Step 4: Ideal solutions
    a_pos = []
    a_neg = []
    for j in range(num_criteria):
        col = [weighted[i][j] for i in range(n)]
        if is_benefit[j]:
            a_pos.append(max(col))
            a_neg.append(min(col))
        else:
            a_pos.append(min(col))
            a_neg.append(max(col))

    # Step 5: Distances
    d_pos = []
    d_neg = []
    for i in range(n):
        dp = math.sqrt(sum((weighted[i][j] - a_pos[j]) ** 2 for j in range(num_criteria)))
        dn = math.sqrt(sum((weighted[i][j] - a_neg[j]) ** 2 for j in range(num_criteria)))
        d_pos.append(dp)
        d_neg.append(dn)

    # Step 6: Closeness coefficient
    results = []
    for i, s in enumerate(services):
        denom = d_pos[i] + d_neg[i]
        c = d_neg[i] / denom if denom > 0 else 0.5

        # Build breakdown from weighted normalized values
        labels = ["cost", "quality", "speed", "reliability"]
        breakdown = {}
        for j, label in enumerate(labels):
            # Convert to 0-1 benefit score for display
            col = [weighted[k][j] for k in range(n)]
            vmin, vmax = min(col), max(col)
            if vmax == vmin:
                breakdown[label] = 1.0
            elif is_benefit[j]:
                breakdown[label] = round((weighted[i][j] - vmin) / (vmax - vmin), 4)
            else:
                breakdown[label] = round((vmax - weighted[i][j]) / (vmax - vmin), 4)

        results.append(ScoredService(
            service=s,
            total_score=round(c, 4),
            breakdown=breakdown,
        ))

    results.sort(key=lambda x: x.total_score, reverse=True)
    for i, r in enumerate(results):
        r.rank = i + 1
        r.reasoning = _generate_reasoning(r, preferences)
    return results


# ──────────────────────────────────────────────
# High-level API
# ──────────────────────────────────────────────

def select_service(
    manifests: list[dict],
    constraints: Constraints | None = None,
    preferences: Preferences | None = None,
    method: str = "topsis",
) -> list[ScoredService]:
    """End-to-end service selection pipeline.
    
    Args:
        manifests: List of ASM manifest dicts
        constraints: Hard constraints for filtering (optional)
        preferences: Soft preference weights (optional, defaults to balanced)
        method: Scoring method — 'weighted_average' or 'topsis'
    
    Returns:
        Ranked list of ScoredService objects
    """
    if preferences is None:
        preferences = Preferences()
    if constraints is None:
        constraints = Constraints()

    # Parse manifests
    services = [parse_manifest(m) for m in manifests]

    # Stage 1: Filter
    filtered = filter_services(services, constraints)

    if not filtered:
        return []

    # Stage 2: Score
    if method == "topsis":
        return score_topsis(filtered, preferences)
    else:
        return score_weighted_average(filtered, preferences)


def load_manifests(directory: str | Path) -> list[dict]:
    """Load all .asm.json files from a directory."""
    path = Path(directory)
    manifests = []
    for f in sorted(path.glob("*.asm.json")):
        with open(f) as fp:
            manifests.append(json.load(fp))
    return manifests


# ──────────────────────────────────────────────
# CLI Demo
# ──────────────────────────────────────────────

def _print_results(results: list[ScoredService], title: str):
    """Pretty-print scoring results."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    for r in results:
        marker = " ← BEST" if r.rank == 1 else ""
        print(f"\n  #{r.rank} {r.service.display_name} — score: {r.total_score:.4f}{marker}")
        print(f"     {r.reasoning}")
        print(f"     cost=${r.service.cost_per_unit:.6f}/unit | "
              f"quality={r.service.quality_score:.3f} | "
              f"latency={r.service.latency_seconds:.2f}s | "
              f"uptime={r.service.uptime:.3f}")
    print()


def main():
    """Demo: load manifests and run through multiple preference scenarios."""
    import sys

    # Determine manifest directory
    script_dir = Path(__file__).parent
    manifest_dir = script_dir.parent / "manifests"

    if not manifest_dir.exists():
        print(f"Error: manifest directory not found at {manifest_dir}")
        sys.exit(1)

    manifests = load_manifests(manifest_dir)
    if not manifests:
        print(f"No .asm.json files found in {manifest_dir}")
        sys.exit(1)

    print(f"Loaded {len(manifests)} ASM manifests from {manifest_dir}")
    for m in manifests:
        print(f"  • {m.get('display_name', m['service_id'])} ({m['taxonomy']})")

    # ── Scenario 1: Cost-first (same taxonomy) ──
    llm_manifests = [m for m in manifests if m["taxonomy"].startswith("ai.llm")]
    if len(llm_manifests) >= 2:
        results = select_service(
            llm_manifests,
            preferences=Preferences(cost=0.5, quality=0.3, speed=0.15, reliability=0.05),
            method="topsis",
        )
        _print_results(results, "Scenario: LLM — Cost Priority (TOPSIS)")

    # ── Scenario 2: Quality-first (same taxonomy) ──
    if len(llm_manifests) >= 2:
        results = select_service(
            llm_manifests,
            preferences=Preferences(cost=0.1, quality=0.7, speed=0.15, reliability=0.05),
            method="topsis",
        )
        _print_results(results, "Scenario: LLM — Quality Priority (TOPSIS)")

    # ── Scenario 3: Cross-category (all services, balanced) ──
    results_wa = select_service(
        manifests,
        preferences=Preferences(cost=0.3, quality=0.3, speed=0.2, reliability=0.2),
        method="weighted_average",
    )
    _print_results(results_wa, "Scenario: Cross-Category — Balanced (Weighted Average)")

    results_topsis = select_service(
        manifests,
        preferences=Preferences(cost=0.3, quality=0.3, speed=0.2, reliability=0.2),
        method="topsis",
    )
    _print_results(results_topsis, "Scenario: Cross-Category — Balanced (TOPSIS)")

    # ── Scenario 4: With constraints ──
    results_filtered = select_service(
        manifests,
        constraints=Constraints(max_latency_s=10),
        preferences=Preferences(cost=0.4, quality=0.4, speed=0.1, reliability=0.1),
        method="topsis",
    )
    _print_results(results_filtered, "Scenario: Filtered (latency ≤ 10s) — Cost+Quality (TOPSIS)")


if __name__ == "__main__":
    main()
