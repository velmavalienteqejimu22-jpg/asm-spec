# Agent Service Manifest: A Standardized Value Description Protocol for Autonomous Service Selection in Multi-Agent Systems

> **Draft — Sections 1-3**
> Authors: Yi Guo
> Date: April 2026

---

## Abstract

The rapid growth of AI-as-a-Service has created an ecosystem where autonomous agents must select among competing services with heterogeneous pricing models, quality characteristics, and reliability guarantees. While existing protocols address service capability discovery (MCP), inter-agent communication (A2A), and secure payment execution (AP2), no standard mechanism exists for agents to evaluate and compare the *economic value* of services in a machine-readable format. We present **Agent Service Manifest (ASM)**, a lightweight JSON Schema protocol that enables service providers to declare standardized value descriptors — covering pricing dimensions, quality benchmarks, SLA parameters, and payment methods — and enables agents to make autonomous, explainable service selection decisions through multi-criteria optimization. ASM is designed as a compatible extension to the Model Context Protocol (MCP), requiring only three mandatory fields while supporting 12 billing dimension types, third-party quality verification, and pre-wired integration with the Agent Payment Protocol (AP2). We validate ASM with 14 real-world service manifests spanning 6 categories (LLM inference, image generation, video generation, text-to-speech, embeddings, and GPU compute), and demonstrate a two-stage selection engine (constraint filtering + TOPSIS ranking) that produces optimal, preference-aware service recommendations. Our evaluation shows that ASM-guided selection achieves 3–10× cost reduction compared to blind selection while maintaining user-specified quality thresholds.

---

## 1. Introduction

The AI service economy is undergoing a fundamental transformation. As autonomous agents become the primary consumers of AI services — invoking language models, generating images, synthesizing speech, and orchestrating compute resources on behalf of human users — the scale and frequency of service selection decisions has grown by orders of magnitude. A single complex agent workflow may require selecting among dozens of candidate services across multiple categories, each with distinct pricing structures, quality profiles, and operational characteristics.

This transformation has been supported by significant advances in agent infrastructure protocols. The **Model Context Protocol** (MCP) [1], introduced by Anthropic and now supported by major platforms including OpenAI and Google, provides a standardized mechanism for agents to discover and invoke external tools. Google's **Agent-to-Agent Protocol** (A2A) [2] enables structured communication between agents, while the **Agent Payment Protocol** (AP2) [3] defines secure transaction execution for agent-initiated purchases. Together, these protocols address the fundamental questions of *what tools can do*, *how agents communicate*, and *how to pay safely*.

However, a critical gap remains: **no existing protocol tells an agent what a service is worth**.

When an agent faces three subtitle generation APIs priced at $0.10/minute, $0.03/minute, and free (with a 5-minute queue), it possesses no structured data to make an informed choice. The pricing information exists only in human-readable HTML pages with inconsistent formats. Quality data is scattered across blog posts, social media discussions, and vendor marketing materials. SLA parameters — latency percentiles, uptime guarantees, rate limits — are buried in documentation that varies wildly in structure and completeness. The result is that **agent intelligence drops to zero at the service selection step**: regardless of how capable the underlying model is, it cannot optimize over information it cannot parse.

This is not merely an efficiency concern — it is a **structural deficiency** in the emerging agent economy. Consider an autonomous coding agent (e.g., Claude Code, Cursor) executing a complex task that requires invoking an LLM (3+ candidates), generating an image (5+ candidates), and running code on a GPU (3+ candidates). If each selection is made blindly — choosing the most expensive, the cheapest, or the most well-known — the total cost can deviate from the optimal by a factor of **3–10×**, with proportional impacts on quality and latency. Multiply this by millions of daily agent transactions, and the aggregate economic waste becomes substantial.

We argue that the root cause is not insufficient model intelligence but **missing data infrastructure**. Just as the Nutrition Facts label transformed consumer food purchasing from subjective judgment to informed comparison, AI services need a standardized, machine-readable "value label" that makes their economic properties computable.

In this paper, we present **Agent Service Manifest (ASM)**, an open protocol designed to fill this gap. ASM provides:

1. **A standardized value descriptor** — a JSON Schema specification covering pricing (12 billing dimension types with tiered and conditional pricing), quality (third-party benchmark references with trust transparency), SLA (latency, throughput, uptime, rate limits), and payment methods (pre-wired for AP2 interop).

2. **A hierarchical taxonomy** — an 18-category classification system (e.g., `ai.llm.chat`, `ai.vision.image_generation`, `infra.compute.gpu`) that enables agents to search, filter, and match services across categories using prefix queries.

3. **A two-stage selection engine** — combining hard constraint filtering with TOPSIS (Technique for Order Preference by Similarity to Ideal Solution) multi-criteria ranking, producing preference-aware recommendations with full explainability.

4. **An MCP-compatible integration path** — ASM can be deployed as an independent `.well-known/asm` endpoint (Phase 1), embedded as `x-asm` annotations in MCP ToolAnnotations (Phase 2), or adopted as native MCP fields (Phase 3), ensuring zero breaking changes at each stage.

We validate ASM with 14 real-world service manifests spanning 6 categories, populated with verified pricing data from production APIs. Our end-to-end demonstration shows that the same set of services produces different optimal selections under different user preference profiles — confirming that service selection is inherently a multi-criteria optimization problem that cannot be solved by heuristics or model intuition alone.

The remainder of this paper is organized as follows. Section 2 formalizes the service selection problem. Section 3 surveys related work. Section 4 presents the ASM protocol design. Section 5 describes the reference implementation. Section 6 evaluates ASM across multiple scenarios. Section 7 discusses limitations, trust mechanisms, and future directions. Section 8 concludes.

---

## 2. Problem Formulation

### 2.1 Setting

We consider a setting where an autonomous agent $\mathcal{A}$ receives a task $T$ from a user $U$ and must select one or more services from a candidate set $\mathcal{S} = \{s_1, s_2, \ldots, s_n\}$ to fulfill the task. Each service $s_i$ is characterized by a multi-dimensional value vector:

$$\mathbf{v}_i = (c_i, q_i, l_i, r_i, \mathbf{e}_i)$$

where:
- $c_i \in \mathbb{R}_{\geq 0}$ is the cost (normalized to a per-unit basis)
- $q_i \in [0, 1]$ is the quality score (normalized from heterogeneous benchmarks)
- $l_i \in \mathbb{R}_{> 0}$ is the latency (p50, in seconds)
- $r_i \in [0, 1]$ is the reliability (uptime probability)
- $\mathbf{e}_i$ is a vector of category-specific extension attributes

### 2.2 User Preferences

The user specifies preferences through two mechanisms:

**Hard constraints** $\mathcal{C}$: A set of inequality predicates that services must satisfy to be considered. For example:

$$\mathcal{C} = \{q_i \geq 0.8, \; l_i \leq 5.0, \; c_i \leq 0.10\}$$

Services violating any constraint are eliminated from the candidate set.

**Soft preferences** $\mathbf{w}$: A weight vector $\mathbf{w} = (w_c, w_q, w_l, w_r)$ where $\sum w_j = 1$ and $w_j \geq 0$, representing the relative importance of each dimension.

### 2.3 Selection Problem

The agent's objective is to find the service $s^*$ that maximizes a preference-weighted multi-criteria score over the feasible set:

$$s^* = \arg\max_{s_i \in \mathcal{S}_{\text{feas}}} \; f(\mathbf{v}_i, \mathbf{w})$$

where $\mathcal{S}_{\text{feas}} = \{s_i \in \mathcal{S} \mid s_i \text{ satisfies } \mathcal{C}\}$ is the set of services passing all hard constraints, and $f$ is a scoring function that maps value vectors and preference weights to a scalar ranking score.

### 2.4 Key Challenges

This formulation reveals several challenges that motivate ASM:

**C1: Heterogeneous pricing.** Real-world AI services use at least 8 distinct billing models — per-input-token, per-output-token, per-image, per-second-of-video, per-character, per-GPU-second, per-request, and subscription-with-credits. A single LLM may bill for both input and output tokens at different rates, with conditional pricing when context exceeds a threshold. Converting these into comparable per-unit costs requires a standardized schema with explicit billing dimension declarations.

**C2: Incommensurable quality.** Quality metrics vary by category: LLMs use Elo scores (LMSYS Arena), image generators use FID (lower is better), TTS systems use MOS (1–5 scale). There is no universal quality score. ASM addresses this by preserving the original metric and scale in the manifest, with normalization performed at scoring time.

**C3: Non-structured information.** Currently, pricing, quality, and SLA data exists primarily in human-readable formats (HTML pricing pages, blog posts, API documentation). LLM-based extraction from these sources is probabilistic, non-reproducible, and costly at scale. For an agent comparing 100 services, reading 300+ web pages would consume thousands of tokens per selection — a cost that dwarfs the savings from better selection.

**C4: Trust asymmetry.** Service providers have economic incentives to overstate quality and understate latency. Without a verification mechanism, agents cannot distinguish self-reported claims from independently verified measurements.

**C5: Preference diversity.** The optimal service depends entirely on who is asking. A user prioritizing cost will choose differently from one prioritizing quality, even when facing the identical candidate set. This rules out any "one size fits all" ranking and necessitates a parameterized scoring function.

### 2.5 Relationship to LLM Routing

It is important to distinguish the ASM selection problem from **LLM routing** as studied in RouteLLM [4] and related work [5]. LLM routing operates *within a single category* (e.g., choosing between GPT-4 and Mixtral for a given query based on predicted difficulty), using ML models trained on preference data. ASM operates *across categories and providers* (e.g., choosing between an LLM service, an image generation service, and a GPU compute service), using structured metadata rather than learned routers. The two are complementary: ASM selects the category and provider, then a system like RouteLLM can further optimize the specific model within that provider.

---

## 3. Related Work

### 3.1 Agent Communication Protocols

The agent protocol landscape has been systematically surveyed by [6], who propose a two-dimensional taxonomy: Context-Oriented (connecting agents to tools/data) versus Inter-Agent (connecting agents to each other), crossed with General-Purpose versus Domain-Specific. MCP [1] occupies the Context-Oriented × General-Purpose quadrant, providing standardized tool discovery and invocation. A2A [2] addresses Inter-Agent communication. The Agent Communication Protocol (ACP) and Agent Network Protocol (ANP) extend these to additional settings.

Critically, this taxonomy has no dimension for **service economics** — none of the surveyed protocols address pricing, quality comparison, or value-based selection. ASM introduces a third dimension to this framework: the Service Economics layer that makes value computable alongside capability and communication.

### 3.2 Agent-as-a-Service

The most closely related academic work is **AaaS-AN** (Agent-as-a-Service based on Agent Network) [7], which proposes a service-oriented agent paradigm based on the RGPS (Role-Goal-Process-Service) standard. AaaS-AN defines a dynamic agent network with service discovery, registration, and orchestration capabilities, validated at the scale of 100+ agent services.

While AaaS-AN and ASM both touch service discovery, their focus is fundamentally different:

| Dimension | AaaS-AN | ASM |
|-----------|---------|-----|
| Core problem | How agents organize and collaborate | How agents evaluate and select services |
| Service discovery | "Who can collaborate" | "Who offers the best value" |
| Pricing support | None | 12 billing dimensions + tiered/conditional |
| Quality metrics | None | Third-party benchmarks + trust flags |
| SLA | None | Latency, throughput, uptime, rate limits |
| Scoring function | None | Filter + TOPSIS with user preferences |

The two are complementary: AaaS-AN orchestrates the agent team, and ASM optimizes each team member's purchasing decisions.

### 3.3 LLM Routing

**RouteLLM** [4] (LMSYS, 4.8K GitHub stars) introduces learned routers that dynamically select between strong and weak LLMs based on query difficulty, achieving 85% cost reduction while maintaining 95% of GPT-4 performance. Four router architectures are evaluated: matrix factorization (recommended), weighted Elo, BERT classifier, and LLM-as-judge.

The **Dynamic Model Routing and Cascading Survey** [5] provides a comprehensive taxonomy of LLM routing approaches, categorizing them by decision timing (pre-routing, mid-generation, post-generation), information used (query features, model metadata, historical performance), and optimization objective (cost, quality, latency).

ASM and LLM routing are complementary systems operating at different levels:

| Dimension | LLM Routing | ASM |
|-----------|-------------|-----|
| Decision timing | Runtime (per-request) | Selection time (per-task) |
| Input data | Query content/difficulty | Structured service metadata |
| Scope | Single category (LLMs only) | Cross-category |
| Method | ML models (trained on preference data) | Mathematical optimization (no training) |
| Complementarity | Optimizes *within* a provider | Optimizes *across* providers and categories |

A complete agent service stack would use ASM to select the category and provider, then RouteLLM (where applicable) to select the specific model.

### 3.4 Secure Payment and Trust

**AP2** (Agent Payment Protocol) [3] by Google defines how agents securely execute payments using Verifiable Digital Credentials (VDCs), Intent Mandates for pre-authorization, and role-separated architecture (user / shopping agent / credential provider / merchant / payment processor). AP2 solves *how to pay* but not *what to buy*.

**Agent Receipts** [8] provides cryptographically signed execution records following the W3C Verifiable Credentials standard, creating an immutable audit trail of agent actions. The ASM-Receipts interoperation forms a complete trust chain: ASM declares expected service quality (pre-selection), the service executes, and a signed receipt records actual delivery (post-execution). Comparing declared vs. actual yields a dynamic trust score:

$$\text{trust}(s_i) = g\left(\sum_{t=1}^{N} \| \mathbf{v}_i^{\text{declared}} - \mathbf{v}_i^{(t), \text{actual}} \| \right)$$

where $g$ is a monotonically decreasing function and $N$ is the number of past transactions.

**Cao et al.** [9] (WWW 2026) address a complementary problem: runtime provider dishonesty (model substitution, token stuffing) through an approximately incentive-compatible mechanism achieving $O(T^{1-\varepsilon} \log T)$ regret. ASM addresses pre-selection information asymmetry, while their mechanism governs post-selection execution honesty.

### 3.5 MCP Ecosystem

The MCP ecosystem has been analyzed from a security perspective by [10], who identify 4 attacker types and 16 threat scenarios across the MCP lifecycle. Their analysis of trust boundaries is directly relevant to ASM: the `self_reported` flag in ASM manifests addresses the same "trusted vs. untrusted server" distinction that MCP's ToolAnnotations acknowledges with its "hints should not be trusted" caveat.

The **MCP 2026 Roadmap** [11] prioritizes transport evolution, agentic communication, governance maturity, and enterprise readiness — but contains **no mention of pricing, marketplace, or service economics**. This confirms that ASM addresses a gap the MCP team has not planned to fill, at least through 2026.

Concurrently, **AWS has released a Marketplace MCP Server** [12] that enables agent-driven product discovery, comparison, and procurement within the AWS Marketplace. This validates the demand for agent-automated service evaluation but implements it as a closed, platform-locked solution. ASM provides the same capability as an open, vendor-neutral standard.

### 3.6 Multi-Criteria Decision Making

ASM's scoring engine draws on the rich MCDM (Multi-Criteria Decision Making) literature, particularly its application to cloud service selection [13]. We adopt **TOPSIS** [14] (Technique for Order Preference by Similarity to Ideal Solution) as our primary ranking method due to its mathematical soundness, computational efficiency, and wide acceptance in the service selection literature. TOPSIS simultaneously considers distance to the positive ideal solution (best possible) and negative ideal solution (worst possible), producing more robust rankings than simple weighted averages that can be skewed by extreme values in a single dimension.

---

## References

[1] Anthropic. Model Context Protocol Specification. 2025. https://spec.modelcontextprotocol.io

[2] Google. Agent-to-Agent Protocol. 2025. https://github.com/google/A2A

[3] Google. Agent Payment Protocol (AP2) V0.1. 2025. https://github.com/anthropics/ap2

[4] I. Ong et al. "RouteLLM: Learning to Route LLMs with Preference Data." arXiv:2406.18665, 2024.

[5] Dynamic Model Routing and Cascading Survey. arXiv:2603.04445, 2026.

[6] A Survey of AI Agent Protocols. arXiv:2504.16736, 2025.

[7] Agent-as-a-Service based on Agent Network (AaaS-AN). arXiv:2505.08446, 2025.

[8] Agent Receipts SDK. https://github.com/agent-receipts/ar

[9] Z. Cao et al. "Pay for the Second-Best Service: A Game-Theoretic Approach Against Dishonest LLM Providers." WWW 2026. arXiv:2511.00847.

[10] MCP Landscape, Security Threats and Future Directions. arXiv:2503.23278, 2025.

[11] MCP 2026 Roadmap. https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/

[12] AWS Marketplace MCP Server. https://docs.aws.amazon.com/marketplace/latest/APIReference/marketplace-mcp-server.html

[13] Cloud Service Selection using MCDM: A Systematic Review. Journal of Network and Systems Management, 2020.

[14] C.L. Hwang and K. Yoon. Multiple Attribute Decision Making: Methods and Applications. Springer, 1981.
