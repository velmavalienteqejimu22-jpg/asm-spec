# X/Twitter Thread — ASM Launch

> 发布时机：GitHub repo 公开后
> 目标受众：MCP 开发者、AI infra 工程师、Agent 开发者
> 语气：技术性但不枯燥，有 hook、有数据、有 demo

---

## Thread

**1/**
Your AI agent is blind when it shops.

MCP tells it what tools CAN DO.
AP2 tells it how to PAY.

But nothing tells it what a tool IS WORTH.

When it faces 3 subtitle APIs at $0.10, $0.03, and free — it literally can't choose. 🧵👇

---

**2/**
This is not a model intelligence problem.

GPT-5 could be infinitely smart. But if service pricing is scattered across HTML pages in 8 different formats, no amount of intelligence helps.

It's a DATA problem. Agents need structured, machine-readable service value data.

---

**3/**
I built Agent Service Manifest (ASM) — an open protocol that gives every AI service a "nutrition label."

One JSON Schema, 5 modules:
• Pricing (12 billing dimensions — per-token, per-image, per-second, tiered, conditional)
• Quality (third-party benchmarks + trust flags)
• SLA (latency p50/p99, uptime, rate limits)
• Payment (API key, Stripe, AP2)
• Extensions (category-specific fields)

---

**4/**
Only 3 required fields: asm_version, service_id, taxonomy.

Everything else is optional. A service exposes what it can.

Designed to embed in MCP ToolAnnotations as `x-asm` — zero breaking changes.

---

**5/**
The key insight: same services, different user preferences → different optimal choices.

"Cost priority" → GPT-4o wins (cheapest per-token)
"Quality priority" → Gemini 2.5 Pro wins (highest Elo)
"Speed priority" → GPT-4o wins (lowest latency)

ASM makes this a computable math problem, not a guess.

---

**6/**
The scorer uses two-stage MCDM:

Stage 1: Filter — hard constraints ("quality ≥ 0.8 AND latency ≤ 5s")
Stage 2: TOPSIS — multi-criteria ranking with user-defined weights

Every decision is explainable: "I chose Service B because your preference is cost-first, and B scored 0.914."

---

**7/**
I validated ASM with 14 real services across 6 categories:

• LLM: Claude Sonnet 4, GPT-4o, Gemini 2.5 Pro
• Image: FLUX 1.1 Pro, DALL-E 3, Imagen 3
• Video: Veo 3.1, Kling 3.0
• TTS: ElevenLabs, OpenAI TTS
• Embedding: text-embedding-3-large, Voyage 3 Large
• GPU: Replicate, RunPod

All with real 2026 pricing data.

---

**8/**
The MCP Server exposes 5 tools:

asm_list — browse all services
asm_query — filter by category, cost, quality, latency
asm_compare — side-by-side comparison
asm_score — ranked recommendations with reasoning
asm_get — full manifest details

Your agent can query it like any other MCP tool.

---

**9/**
"Why not just let the LLM read pricing pages?"

• Cost: thousands of tokens per comparison vs. near-zero for structured JSON
• Accuracy: LLMs misparse complex tiered pricing ~30% of the time
• Reproducibility: ask twice, get different answers. ASM scorer is deterministic
• Scale: 3 services = fine. 100 services = impossible without structure

---

**10/**
Trust model — three layers:

L1: `self_reported` flag → agent knows who made the claim
L2: Third-party benchmark references → independently verifiable
L3: Signed Receipts → ASM declares quality, receipt proves delivery, trust score updates

ASM + @agent_receipts = complete trust chain for agent commerce.

---

**11/**
AWS already shipped a Marketplace MCP Server for agent-driven product comparison.

Proof the demand is real.

But it's closed and platform-locked.

ASM is the open standard version. Like OpenAPI vs. API Gateway.

---

**12/**
MCP 2026 Roadmap focuses on transport, agentic communication, governance, and enterprise readiness.

No mention of pricing, marketplace, or service economics.

The window is open. ASM fills the gap.

---

**13/**
What's next:

→ GitHub repo (live now): [LINK]
→ SEP proposal to MCP specification
→ arXiv preprint (May)
→ Anthropic AI Hackathon (May 26)
→ Signed Receipts integration demo

If you're building agent infrastructure, I'd love your feedback.

Star the repo, open an issue, or DM me. 🙏

---

## Posting Notes

- **Attach to tweet 5**: Image showing 3 scenarios with different scores (from e2e demo output)
- **Attach to tweet 7**: Table/image of 14 services across 6 categories
- **Attach to tweet 8**: Screenshot of MCP Server tools in Claude Desktop
- **Tag**: @AnthropicAI @modelaboratory @alexalbert__ (if found on X)
- **Best time**: Tuesday/Wednesday, 8-10 AM Pacific
- **Hashtags** (on last tweet only): #MCP #AIAgents #OpenProtocol
