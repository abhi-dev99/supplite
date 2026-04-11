# AITHON Presentation Content — Team Lite
### "The Supply Chain Sees the Future"

---

## Slide 1 — Title Slide
*(No changes needed — use as-is)*

---

## Slide 2 — Instructions
*(Reference only — do not present)*

---

## Slide 3 — Judging Criteria
*(Reference only — do not present)*

---

## Slide 4 — TEAM SLIDE

| Field | Content |
|---|---|
| **Domain** | Supply Chain |
| **Team Name** | lite |
| **Team Members** | Abhishek Saraf, Aditya Shah, Aayush Wase |
| **Problem Statement** | The Supply Chain Sees the Future |

---

## Slide 5 — Problem Statement

### Clearly Define the Problem

- **The Speed Mismatch:** Global procurement moves in months, but modern consumer demand shifts overnight.
- **Siloed Intelligence:** Supply chains forecast using backward-looking historical sales, completely ignoring real-time external catalysts and volatile regional trends.
- **The Dual Crisis:** This reporting latency traps billions of dollars in dead safety stock, while simultaneously causing massive out-of-stocks on viral inventory.

### Why It Matters

- **Systemic Inefficiency:** Supply chains are currently designed for a world of geographic stability, but we operate in an era of hyper-local volatility. You cannot manage modern inventory velocity using static historical models.
- **The Execution Gap:** Operators on the ground (like buyers and DC managers) are drowning in fragmented dashboards. They lack the capacity to manually synthesize complex global and demographic signals into daily, node-level purchasing decisions.
- **The Ultimate Cost:** The failure to fuse diverse data streams into a cohesive, actionable consensus leads directly to immense carrying costs and lost opportunity—a structural vulnerability that traditional software cannot solve.

---

## Slide 6 — Solution Overview

### High-Level Solution

**SupplyLite: An ML-driven demand intelligence platform that fuses internal sales data with external real-estate and demographic signals to predict stockouts and overstock weeks before they become inevitable — and tells the buyer exactly what to do about it, in plain language.**

We don't just forecast demand. We build an early warning system that:
1. **Detects** — Flags at-risk SKUs using a trained XGBoost classifier across 11 metro regions
2. **Explains** — Generates plain-language AI reasoning for every alert ("Days of supply < lead time. Forecast shortfall: 1,694 units over 60d.")
3. **Localizes** — Filters intelligence to the buyer's specific distribution center, because a buyer in Atlanta doesn't need Oakland's data
4. **Visualizes** — Renders demand heatmaps on an interactive 3D logistics map overlaid with real U.S. Census housing data

### Key Features

- **ML Demand Forecasting** — XGBoost model trained on 120K+ rows of synthetic sales, signals, and inventory data across 11 metro areas
- **External Signal Fusion** — Real-time U.S. Census ACS DP04 housing data (renter share, vacancy rates) fused as demand indicators
- **Buyer-Centric Dashboard** — DC-specific filtering, plain-language risk reasoning, sortable/filterable inventory grid
- **Interactive Logistics Map** — Deck.gl-powered 3D heatmap with state boundaries, store markers, and DC territory overlays
- **Anomaly Detection** — Trajectory shift alerts that flag when a product's demand velocity suddenly changes
- **Signal Timeline** — Historical trend visualization showing how ML signals evolved over time

---

## Slide 7 — AI Assisted Problem Solving

### How AI Helped Break Down the Problem

- **Problem Decomposition**: Used Claude Opus 4.6 to decompose the problem statement into sub-problems: data generation, feature engineering, model training, inference pipeline, and frontend visualization. AI helped us map each challenge in the PS (viral spike, silent overstock, seasonal blindspot, correlated signals) to specific model features
- **Data Architecture Design**: AI was instrumental in designing the synthetic dataset schema — 120K+ rows across sales, signals, and inventory CSVs — ensuring realistic temporal patterns, seasonal effects, and cross-correlated external signals
- **Feature Engineering Strategy**: AI helped identify which features would give the model the most predictive power — composite demand indices, renter share percentages, days-of-supply-to-lead-time ratios, and rolling signal volumes
- **Iterative Model Refinement**: We used AI to debug feature importance, tune XGBoost hyperparameters, and validate that the model wasn't overfitting by stress-testing with out-of-distribution data

### Iterations & Learning

- **V1** → Basic demand classifier with just sales data → poor signal detection
- **V2** → Added external signal features (social volume, search trends) → improved recall on stockout prediction
- **V3** → Fused real estate data (Census ACS DP04) as a leading demand indicator → demand spikes now correlated with housing market activity in metro regions
- **V4** → Added anomaly detection flags and plain-language reasoning → the buyer now understands *why*, not just *what*

---

## Slide 8 — AI Engineering

### Tools Used (LLMs, APIs, MCP Servers)

| Tool | Role |
|---|---|
| **Claude Opus 4.6** | Primary reasoning engine for architecture decisions, complex debugging, and presentation content |
| **Claude Sonnet 4.6** | Rapid iteration on frontend components, CSS design systems, and React state management |
| **Claude Haiku 4.5** | Lightweight validation checks and quick code reviews |
| **Gemini 3.1 Pro** | Data pipeline design, model training scripts, feature engineering logic |
| **Gemini 3.1 Flash** | Fast prototyping and exploratory analysis |
| **GPT-5.3 Codex (Xhigh)** | High-quality code generation for critical pipeline components |
| **Stitch MCP** | UI design system prototyping via AntiGravity agent integration |
| **Figma MCP** | Design-to-code workflow for dashboard layout and component architecture |

### Prompt Strategy

- **Detailed & Domain-Specific**: Prompts included explicit supply chain context (lead times, DC operations, buyer workflows) to reduce hallucination
- **Multi-Layered**: Complex tasks were decomposed into sequential prompt chains — e.g., "Design the schema" → "Generate the data" → "Validate edge cases" → "Build the model"
- **Adversarial Validation**: We actively challenged AI outputs — when the model training script was tested on training data, we caught it immediately and forced out-of-distribution validation
- **Context Anchoring**: Used file references and conversation history to maintain coherence across long development sessions

### Hallucination & Error Handling

- **Import Errors**: AI occasionally generated imports for packages not in our dependency tree (`@deck.gl/core` instead of `deck.gl`). Caught via Vite build validation, fixed in real-time
- **Data Integrity**: AI-generated synthetic datasets were manually reviewed row-by-row (120K+ rows) to ensure temporal consistency, realistic stock levels, and proper SKU-to-metro mapping
- **Overfitting Prevention**: When AI suggested testing the model on training data, we identified the flaw and enforced proper train/test splits with out-of-distribution validation

---

## Slide 9 — Technical Architecture

### Systems Design

```
┌─────────────────────────────────────────────────────────┐
│                    DATA GENERATION                       │
│  Python scripts generate 120K+ rows of synthetic data   │
│  (sales.csv, signals.csv, inventory.csv)                │
│  + US Census ACS DP04 real estate data integration      │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│                 FEATURE ENGINEERING                      │
│  Composite demand index, rolling signal volumes,         │
│  renter share %, days-of-supply ratios, anomaly flags   │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   ML MODEL LAYER                        │
│  XGBoost Classifier → Risk classification               │
│  (STOCKOUT_RISK / OVERSTOCK_RISK / OK / WATCH)          │
│  Output: training_report.json + model artifacts         │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│               FRONTEND INTELLIGENCE HUB                 │
│  React 19 + Vite 8 + Deck.gl (3D Map) + Recharts       │
│  Enterprise glassmorphism UI, DC-specific filtering,    │
│  buyer briefs, interactive logistics grid               │
└─────────────────────────────────────────────────────────┘
```

### Tech Stack

> **INSERT: `tech_stack_diagram.png`** (generated image in the ppt folder)

| Layer | Technologies |
|---|---|
| **Data Pipeline** | Python 3.11, Pandas, US Census Bureau API (ACS DP04) |
| **ML / Intelligence** | Scikit-learn, XGBoost, Custom Feature Engineering |
| **Frontend** | React 19, Vite 8, Deck.gl (WebGL), Recharts, Lucide Icons |
| **Design** | CSS Glassmorphism, Outfit/Inter Typography, Mesh Gradients |
| **AI Toolchain** | Claude Opus/Sonnet 4.6, Gemini 3.1 Pro/Flash, GPT-5.3, Stitch MCP, Figma MCP |

---

## Slide 10 — Prototype/Demo

*(This is a live demo slide — present the running dashboard)*

### Demo Flow (suggested 3-minute walkthrough):

1. **Landing — Intelligence Hub**: Show the hero metrics (Critical Shortages, Capital Exposure, Trajectory Shifts) and the integrated logistics map
2. **Map Interaction**: Hover over the map to expand it. Show state boundaries, heatmap intensity clusters around the 11 metro areas, DC node markers
3. **DC Filtering**: Select "Braselton DC" from the Active Node dropdown → watch the map fly to Georgia, metrics recalculate to local node values
4. **Data Grid**: Scroll through the SKU inventory grid. Click column headers to sort. Show the "ORDER NOW" vs "OK" badges, runway depletion bars, and AI reasoning column
5. **Signal Timeline**: Navigate to Signal Timeline view → show how demand signals evolved over time with the Recharts visualization
6. **Buyer Brief**: Navigate to Buyer Brief → show the plain-language weekly action summary

### Key talking points during demo:
- "The buyer sees only their DC's data — not the whole company"
- "Every risk flag comes with a plain-language explanation"
- "The map shows real Census housing data fused with our demand model"
- "This isn't a dashboard — it's a decision engine"

---

## Slide 11 — Challenges & Learning

### Challenges Faced in Using AI

- **Hallucinations and incorrect responses** — AI occasionally generated plausible-looking but broken code (wrong import paths, duplicate declarations, missing dependency references). These compiled silently but crashed at runtime
- **Context window drift** — In long development sessions, AI would lose track of earlier architectural decisions, requiring explicit re-anchoring
- **Over-engineering bias** — AI tended to suggest overly complex solutions (e.g., full SHAP integration, Kubernetes deployments) when simpler approaches were more appropriate for a hackathon prototype

### How Did Your Team Overcome?

- **Manual dataset validation** — Reviewed all 120K+ rows of synthetic data down to the last detail, found temporal inconsistencies and SKU mapping errors, and fixed them systematically (using AI for the fixes, but human judgment for the detection)
- **Build-first debugging** — Ran `vite build` after every significant change to catch compilation errors before they became white-screen runtime crashes
- **Adversarial prompting** — Actively challenged AI suggestions ("If you're testing on the same data you trained on, of course it'll say it's correct") to force better engineering practices

### If You Have Unlimited Time & Money

- **Real-time external signal ingestion** — Live social media monitoring (TikTok/Instagram API), Google Trends integration, and event calendar data for regional demand spikes
- **SHAP explainability** — Add SHAP value visualizations to every risk flag so the buyer can see exactly which features drove the prediction
- **LLM-powered buyer briefs** — Use Claude Opus 4.6 API for dynamically generated, surgical weekly action briefs per DC
- **Cloud deployment** — AWS (ECS + RDS + S3) for production-grade infrastructure with auto-scaling
- **Live data connectors** — Replace synthetic data with real WSI inventory feeds and POS data

---

## Slide 12 — Feedback

### Anything else you would like to mention to us?

This project was built entirely with AI-assisted engineering in under 48 hours. Every line of code — from the ML pipeline to the 3D map renderer — was written through human-AI collaboration. We didn't just use AI as a code generator; we used it as a thinking partner to decompose a $2B+ industry problem into an actionable intelligence platform.

The key insight: **the buyer is the user, not the data scientist.** Every design decision — from the glassmorphism UI to the plain-language reasoning column — was made to ensure that a distribution center buyer with zero technical background can make $12M inventory decisions in under 30 seconds.

### How was your experience with the WSI AI-thon? What can we do to improve next year?

- **Providing a sample company dataset** (even anonymized/synthetic) would dramatically improve solution quality — participants could build on real distribution patterns rather than generating synthetic data from scratch
- **Access to WSI's actual DC network topology** would enable more realistic geographic modeling
- Incredible problem statement — the viral spike scenario is exactly the kind of real-world challenge that makes hackathons meaningful
