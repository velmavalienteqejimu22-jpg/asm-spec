#!/usr/bin/env python3
"""
ASM End-to-End Demo
===================

Simulates an agent receiving a task, querying the ASM registry,
scoring candidates, and making an explained service selection.

This demonstrates the complete ASM value chain:
  Task → Taxonomy → Registry Query → Filter → Score → Select → Explain

No external dependencies required (pure Python + ASM scorer).
"""

import sys
import os

# Add scorer to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scorer"))

from scorer import (
    load_manifests,
    select_service,
    Constraints,
    Preferences,
    ScoredService,
)

# ── ANSI colors ─────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"
STAR = "⭐"


def header(text: str):
    print(f"\n{BOLD}{CYAN}{'═' * 70}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 70}{RESET}")


def step(num: int, text: str):
    print(f"\n{BOLD}{YELLOW}  Step {num}: {text}{RESET}")


def result_line(text: str, indent: int = 4):
    print(f"{' ' * indent}{GREEN}→{RESET} {text}")


def dim_line(text: str, indent: int = 4):
    print(f"{' ' * indent}{DIM}{text}{RESET}")


def print_ranking(results: list[ScoredService], top_n: int = 5):
    for r in results[:top_n]:
        marker = f" {STAR} {GREEN}SELECTED{RESET}" if r.rank == 1 else ""
        bar_len = int(r.total_score * 30)
        bar = f"{'█' * bar_len}{'░' * (30 - bar_len)}"
        print(f"    #{r.rank} {BOLD}{r.service.display_name:30s}{RESET} "
              f"[{bar}] {r.total_score:.4f}{marker}")
        dim_line(
            f"cost={r.breakdown['cost']:.2f} quality={r.breakdown['quality']:.2f} "
            f"speed={r.breakdown['speed']:.2f} reliability={r.breakdown['reliability']:.2f}",
            indent=8,
        )


# ── Demo Scenarios ──────────────────────────────────────

def scenario_1(manifests: list[dict]):
    """User asks: "I need a cheap but decent LLM for my chatbot" """
    header("Scenario 1: \"I need a cheap but decent LLM for my chatbot\"")

    step(1, "Task Analysis")
    result_line("Identified need: LLM chat model")
    result_line("Taxonomy: ai.llm.chat")

    step(2, "Registry Query")
    llm_manifests = [m for m in manifests if m["taxonomy"] == "ai.llm.chat"]
    result_line(f"Found {len(llm_manifests)} services in ai.llm.chat")
    for m in llm_manifests:
        dim_line(f"• {m['display_name']} ({m['service_id']})")

    step(3, "User Preferences")
    result_line("Priority: cost-first, quality must be decent")
    result_line("Constraints: quality ≥ 0.75")
    result_line("Weights: cost=0.50, quality=0.30, speed=0.15, reliability=0.05")

    step(4, "Score & Rank (TOPSIS)")
    results = select_service(
        llm_manifests,
        constraints=Constraints(min_quality=0.75),
        preferences=Preferences(cost=0.50, quality=0.30, speed=0.15, reliability=0.05),
        method="topsis",
    )
    print_ranking(results)

    step(5, "Decision")
    if results:
        best = results[0]
        result_line(f"Selected: {BOLD}{best.service.display_name}{RESET}")
        result_line(f"Reason: {best.reasoning}")


def scenario_2(manifests: list[dict]):
    """User asks: "Generate a product image, highest quality possible" """
    header("Scenario 2: \"Generate a product image, highest quality possible\"")

    step(1, "Task Analysis")
    result_line("Identified need: Image generation")
    result_line("Taxonomy: ai.vision.image_generation")

    step(2, "Registry Query")
    img_manifests = [m for m in manifests if m["taxonomy"] == "ai.vision.image_generation"]
    result_line(f"Found {len(img_manifests)} services in ai.vision.image_generation")
    for m in img_manifests:
        dim_line(f"• {m['display_name']} ({m['service_id']})")

    step(3, "User Preferences")
    result_line("Priority: quality-first, cost doesn't matter")
    result_line("Weights: cost=0.05, quality=0.70, speed=0.15, reliability=0.10")

    step(4, "Score & Rank (TOPSIS)")
    results = select_service(
        img_manifests,
        preferences=Preferences(cost=0.05, quality=0.70, speed=0.15, reliability=0.10),
        method="topsis",
    )
    print_ranking(results)

    step(5, "Decision")
    if results:
        best = results[0]
        result_line(f"Selected: {BOLD}{best.service.display_name}{RESET}")
        result_line(f"Reason: {best.reasoning}")


def scenario_3(manifests: list[dict]):
    """User asks: "I need TTS for my podcast, voice quality matters most" """
    header("Scenario 3: \"I need TTS for my podcast, voice quality matters most\"")

    step(1, "Task Analysis")
    result_line("Identified need: Text-to-speech")
    result_line("Taxonomy: ai.audio.tts")

    step(2, "Registry Query")
    tts_manifests = [m for m in manifests if m["taxonomy"] == "ai.audio.tts"]
    result_line(f"Found {len(tts_manifests)} services in ai.audio.tts")
    for m in tts_manifests:
        dim_line(f"• {m['display_name']} ({m['service_id']})")

    step(3, "User Preferences")
    result_line("Priority: quality-first (podcast = voice matters)")
    result_line("Weights: cost=0.10, quality=0.65, speed=0.10, reliability=0.15")

    step(4, "Score & Rank (TOPSIS)")
    results = select_service(
        tts_manifests,
        preferences=Preferences(cost=0.10, quality=0.65, speed=0.10, reliability=0.15),
        method="topsis",
    )
    print_ranking(results)

    step(5, "Decision")
    if results:
        best = results[0]
        result_line(f"Selected: {BOLD}{best.service.display_name}{RESET}")
        result_line(f"Reason: {best.reasoning}")


def scenario_4(manifests: list[dict]):
    """User asks: "Make a short video clip, keep it under budget" """
    header("Scenario 4: \"Make a short video clip, keep it under budget\"")

    step(1, "Task Analysis")
    result_line("Identified need: Video generation")
    result_line("Taxonomy: ai.video.generation")

    step(2, "Registry Query")
    vid_manifests = [m for m in manifests if m["taxonomy"] == "ai.video.generation"]
    result_line(f"Found {len(vid_manifests)} services in ai.video.generation")
    for m in vid_manifests:
        dim_line(f"• {m['display_name']} ({m['service_id']})")

    step(3, "User Preferences")
    result_line("Priority: budget-conscious, speed matters")
    result_line("Weights: cost=0.50, quality=0.20, speed=0.20, reliability=0.10")

    step(4, "Score & Rank (TOPSIS)")
    results = select_service(
        vid_manifests,
        preferences=Preferences(cost=0.50, quality=0.20, speed=0.20, reliability=0.10),
        method="topsis",
    )
    print_ranking(results)

    step(5, "Decision")
    if results:
        best = results[0]
        result_line(f"Selected: {BOLD}{best.service.display_name}{RESET}")
        result_line(f"Reason: {best.reasoning}")


def scenario_5(manifests: list[dict]):
    """Cross-category: Agent has a complex task needing multiple services"""
    header("Scenario 5: Cross-Category — \"Summarize a video, generate thumbnail, add voiceover\"")

    step(1, "Task Decomposition")
    result_line("Sub-task A: LLM to summarize video transcript → ai.llm.chat")
    result_line("Sub-task B: Generate thumbnail image → ai.vision.image_generation")
    result_line("Sub-task C: Generate voiceover → ai.audio.tts")

    subtasks = [
        ("ai.llm.chat", "LLM for summarization", Preferences(cost=0.40, quality=0.35, speed=0.20, reliability=0.05)),
        ("ai.vision.image_generation", "Image for thumbnail", Preferences(cost=0.20, quality=0.55, speed=0.15, reliability=0.10)),
        ("ai.audio.tts", "TTS for voiceover", Preferences(cost=0.15, quality=0.60, speed=0.10, reliability=0.15)),
    ]

    total_cost_estimate = 0.0
    selections = []

    for i, (taxonomy, desc, prefs) in enumerate(subtasks):
        step(2 + i, f"Sub-task: {desc} ({taxonomy})")
        candidates = [m for m in manifests if m["taxonomy"] == taxonomy]
        result_line(f"Candidates: {len(candidates)}")

        results = select_service(candidates, preferences=prefs, method="topsis")
        print_ranking(results, top_n=3)

        if results:
            best = results[0]
            selections.append(best)
            total_cost_estimate += best.service.cost_per_unit
            result_line(f"Selected: {BOLD}{best.service.display_name}{RESET} "
                       f"(cost/unit: ${best.service.cost_per_unit:.6f})")

    step(5, "Pipeline Summary")
    for s in selections:
        result_line(f"{s.service.taxonomy} → {BOLD}{s.service.display_name}{RESET} (score: {s.total_score:.4f})")
    result_line(f"Estimated total cost per unit: ${total_cost_estimate:.6f}")


# ── Main ────────────────────────────────────────────────

def main():
    manifest_dir = os.path.join(os.path.dirname(__file__), "..", "manifests")
    manifests = load_manifests(manifest_dir)

    print(f"\n{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}  ASM End-to-End Demo — Agent Service Manifest v0.2{RESET}")
    print(f"{BOLD}  \"OpenAPI describes what a service can do.{RESET}")
    print(f"{BOLD}   ASM describes what a service is worth.\"{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}")
    print(f"\n  Loaded {BOLD}{len(manifests)}{RESET} service manifests across "
          f"{BOLD}{len(set(m['taxonomy'] for m in manifests))}{RESET} categories")

    # Taxonomy overview
    from collections import Counter
    tax_counts = Counter(m["taxonomy"] for m in manifests)
    for tax, count in sorted(tax_counts.items()):
        dim_line(f"• {tax}: {count} service(s)")

    # Run all scenarios
    scenario_1(manifests)
    scenario_2(manifests)
    scenario_3(manifests)
    scenario_4(manifests)
    scenario_5(manifests)

    # Final summary
    header("Demo Complete")
    print(f"""
  {BOLD}What you just saw:{RESET}
  1. Agent receives natural language task
  2. Task → taxonomy mapping (what kind of service is needed)
  3. ASM Registry query (structured service discovery)
  4. Filter + TOPSIS scoring (multi-criteria decision making)
  5. Explained selection (auditable, reproducible)

  {BOLD}Key insight:{RESET}
  Same 14 services, different user preferences → different optimal choices.
  ASM makes this decision {GREEN}computable, explainable, and automatable{RESET}.

  {DIM}Learn more: https://github.com/asm-protocol/asm-spec{RESET}
""")


if __name__ == "__main__":
    main()
