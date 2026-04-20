# MaRe Head Spa — Growth Engine

A boutique automation platform for **MaRe**, a luxury head-health system that
pairs professional scalp assessment with high-end Italian cosmetics.

This repo is the growth engine behind MaRe's nationwide expansion. It solves
the **Personalized Scale Paradox**: reaching thousands of high-revenue salons
and discerning customers *without* degrading the hyper-premium brand.

## Focus pillars (current scope)

| # | Pillar | What it does |
|---|--------|--------------|
| 2 | **Luxury-Standard Outreach** | Generates personalized B2B messages that speak fluent "Salon Lingo" and strip out AI-ish tells. |
| 3 | **High-Volume Content Synthesis** | Scales YouTube Shorts scripts, blogs, and social assets from ~1/wk to 50+/wk while holding brand standard. |

*(Pillars 1 "Revenue-Verified Prospecting" and 4 "Customer Awareness / AI-search
dominance" are descoped for this iteration but the architecture leaves room.)*

## Repo layout

```
.
├── .env.example              # Copy to .env and fill GEMINI_API_KEY
├── Brand Kit/                # Official MaRe brand-kit PDFs (gitignored)
├── backend/                  # Python — Gemini, agents, pipelines
│   ├── pyproject.toml
│   └── src/mare/
│       ├── brand/            # identity (palette/typography/persona/tone),
│       │                     # voice, vocabulary, salon lingo, AI-red-flags
│       ├── outreach/         # Pillar 2 — email, LinkedIn DM, postcard
│       ├── content/          # Pillar 3 — shorts, blogs, social, image
│       │                     # prompts, Imagen 4 renderer, channel matrix
│       ├── workflow/         # LangGraph HITL state machine + SQLite store
│       ├── gemini_client.py  # Thin wrapper around google-genai
│       ├── config.py         # Loads .env
│       └── cli.py            # `python -m mare ...`
└── frontend/                 # Next.js dashboard (placeholder)
```

## Quick start

### 1. Set your Gemini key

```bash
cp .env.example .env           # if you haven't already
# Then edit .env and paste your key into GEMINI_API_KEY
```

Get a key at https://aistudio.google.com/app/apikey.

### 2. Install the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Smoke test Gemini

```bash
python -m mare ping
```

You should see a short, on-brand reply from Gemini.

### 4. Try the pillars

```bash
# --- Pillar 2 — Hyper-Personalized Outreach ---

# Email + LinkedIn DM, anchored on a real social-media moment
python -m mare outreach draft \
  --salon-name "Maison Noir" --city Aspen --owner Camille \
  --revenue 2400000 \
  --specialty "color correction" \
  --note "Featured in Allure 2024 for their weekend color-correction waitlist" \
  --highlight "instagram|Reel last week about a 4-hour brunette-to-blonde color correction"

# Luxury direct-mail postcard concept (front image + back copy + production)
python -m mare outreach postcard \
  --salon-name "Maison Noir" --city Aspen --owner Camille \
  --highlight "instagram|Post pinned to top of grid shows their private suite with natural light"

# --- Pillar 3 — Luxury Content Engine ---

# Single YouTube Short script (with AI-search block: target queries + LLM summary + entities)
python -m mare content short --topic "Dandruff solutions for color-treated hair"

# Short + per-beat image prompts (Midjourney v6, Imagen 3, generic)
python -m mare content image-prompts --topic "A realistic hair-care routine that actually works"

# Short + ready-to-submit HeyGen v2 job spec (dry-run unless HEYGEN_API_KEY is set)
python -m mare content heygen-spec --topic "Why scalp health is the first step of any hair routine"

# Full package: Short + Blog + IG + LinkedIn from one brief
python -m mare content package --topic "The case for a 20-minute head ritual before every color service"

# Real rendered images via Imagen 4 (per-beat PNGs for a Short)
python -m mare content render-images --topic "A 30-second mirror test for scalp health" --tier standard
```

### 5. Ship via the MaRe-Verified workflow (human-in-the-loop)

Nothing is "MaRe Verified" without a human stamp. The workflow persists every
draft to SQLite so review can take minutes, hours, or days — no context is lost.

```bash
# Submit a draft into the approval queue (works for any asset kind)
python -m mare workflow submit-short --topic "Scalp detox is a ritual, not a product"
python -m mare workflow submit-blog --topic "Dandruff solutions that don't strip color"
python -m mare workflow submit-outreach --salon-name "Maison Noir" --city Aspen \
  --owner Camille --highlight "instagram|Reel last week on a color correction"
python -m mare workflow submit-postcard --salon-name "Maison Noir" --city Aspen --owner Camille

# Review queue
python -m mare review pending                      # list everything awaiting review
python -m mare review show <thread_id>             # see draft, lint report, revision history
python -m mare review approve <thread_id> --reviewer rebecca
python -m mare review revise  <thread_id> --notes "Cut the tricolons; drop 'wellness' from VO2."
python -m mare review reject  <thread_id> --reason "Off-brand angle."
```

Approved drafts land as **MaRe-Verified artifacts** at
`artifacts/verified/<kind>/<thread_id>.md` with YAML frontmatter (reviewer,
timestamp, iterations). Your dispatcher/sender picks up from there.

## Design principles

1. **Brand is a first-class citizen.** Every prompt pulls from `mare.brand` —
   the official brand-kit identity (`mare.brand.identity`: essence, persona,
   12-trait tone matrix, full color palette with hex codes, typography,
   logo rules), tone rules, salon lingo, canonical product names (MaRe Capsule,
   MaRe Eye, MaRe x Philip Martin's...), pillar vocabulary (Systematic / Luxury /
   Natural-Organic / Wellness), and an AI-ish blacklist (no "delve", no em-dashes,
   no "in today's fast-paced world"). Change these once, every generator inherits.
   The source-of-truth PDFs live in `Brand Kit/`; `mare.brand.identity` is a
   verbatim transcription.
2. **Humans review, agents draft.** Outputs land in `artifacts/` for a human
   to polish before send/publish. Nothing auto-sends.
3. **Structured output by default.** Every generator declares a Pydantic schema
   and the Gemini SDK enforces it server-side. No brittle JSON-string parsing.
4. **Two-tier model strategy.** Reasoning tasks (outreach personalization, postcard
   ideation, blog writing) use `GEMINI_REASONING_MODEL` (default `gemini-2.5-pro`).
   Bulk drafting (Shorts, social captions) uses `GEMINI_MODEL` (default `gemini-2.5-flash`)
   to keep costs sane at 50x output.
5. **AI-search first, SEO second.** Every blog and Short ships with a machine-readable
   AI-search block: target queries, a cite-ready LLM summary, named entities,
   topical facets, and FAQPage JSON-LD. These are the dials that decide whether
   ChatGPT Search, Google SGE, and Perplexity cite MaRe for *"dandruff solutions"*
   or *"luxury head spa near me"*.
6. **Mobile-first across every channel.** MaRe content is consumed on a phone
   first, a desktop second, a printed piece third — and the pipeline enforces
   that hierarchy at the frame level. `mare.content.channels` is the registry
   of every distribution surface (YouTube Shorts, IG Reel/Story/Feed/Carousel,
   TikTok, LinkedIn, blog hero, email hero, direct-mail postcard) with its
   target aspect, Imagen-native render aspect, safe-area rule, and platform
   notes. Pick a channel with `--channel ig_feed` (or `blog_hero`, `tiktok`,
   etc.) and the image-prompt generator + Imagen 4 renderer + downstream
   crop guidance all tune to it.

## Mobile-first channel matrix

Every digital asset is framed for a thumb-held screen first. Imagen 4 can
natively render `1:1`, `3:4`, `4:3`, `9:16`, `16:9` — channels whose target
aspect isn't in that set (e.g. IG Feed `4:5`, postcard `5:7`) render at the
nearest native aspect and a downstream crop brings them home without
amputating the subject.

| Channel id | Label | Target | Imagen renders at | Mobile-first |
|---|---|---|---|---|
| `youtube_short` | YouTube Shorts | 9:16 | 9:16 | ✓ |
| `ig_reel` | Instagram Reels | 9:16 | 9:16 | ✓ |
| `ig_story` | Instagram Stories | 9:16 | 9:16 | ✓ |
| `tiktok` | TikTok | 9:16 | 9:16 | ✓ |
| `ig_feed` | Instagram Feed post | 4:5 | 3:4 + crop | ✓ |
| `ig_carousel` | Instagram Carousel | 4:5 | 3:4 + crop | ✓ |
| `linkedin_post` | LinkedIn post | 4:5 | 3:4 + crop | ✓ |
| `blog_hero` | Blog hero image | 16:9 | 9:16 + crop | ✓ (mobile is default, desktop is a derivative) |
| `email_hero` | Email hero | 4:5 | 3:4 + crop | ✓ |
| `postcard_front` | Direct-mail postcard | 5:7 | 3:4 + crop | print |

Run `python -m mare content channels` to see the matrix any time. Change
frames or safe areas in `backend/src/mare/content/channels.py` and every
generator inherits the change automatically.

```bash
# Render a Short as 9:16 (the default)
python -m mare content render-images --topic "A 30-second mirror test for scalp health"

# Same Short, re-framed for an Instagram Feed post
python -m mare content render-images --topic "A 30-second mirror test for scalp health" \
  --channel ig_feed

# Blog hero — mobile 9:16 is the master; 16:9 is a crop served to desktop only
python -m mare content render-images --topic "How to read your scalp" \
  --channel blog_hero --tier ultra
```

## How the human-in-the-loop gate works

Yes — the HITL gate is triggered by **LangGraph's `interrupt()`** primitive.
The workflow is a state machine with a durable SQLite checkpointer, so a
draft can sit for minutes, hours, or days waiting for a human without
losing context.

```
           submit-short / submit-blog / submit-outreach / submit-postcard
                                    │
                                    ▼
                                 ┌─────┐
                                 │draft│  (Gemini 2.5 Pro, Flash fallback)
                                 └──┬──┘
                                    ▼
                              ┌───────────┐
                              │ auto_lint │  (AI-ish red flags, vocab coverage,
                              └──────┬────┘   tricolon / em-dash counts)
                                     ▼
                          ┌──────────────────────┐
                          │    human_review      │  ← LangGraph interrupt()
                          │    (PAUSES HERE)     │  State persists to SQLite.
                          └──────────┬───────────┘  `mare review pending` lists it.
                                     │
      ┌──────────────────────────────┼────────────────────────────┐
      │                              │                            │
      ▼                              ▼                            ▼
 `review approve`              `review revise`              `review reject`
   (+ reviewer)               (+ notes → re-prompt)         (+ reason)
      │                              │                            │
      ▼                              ▼                            ▼
   publish                 back to draft (iteration++)       force_reject
  artifacts/verified/          up to 3 revision loops             END
  with YAML frontmatter
  (mare_verified: true)
```

Under the hood: `human_review_node` calls `interrupt({...})` which snapshots
the full graph state to the SQLite checkpointer and yields. The `mare review
approve/revise/reject` commands resume the graph with `Command(resume=...)`
carrying the reviewer's decision, so the graph picks up exactly where it
paused and routes via `route_after_review`. Nothing is "MaRe Verified"
without a human explicitly approving it.

## Model configuration

MaRe runs on Gemini 2.5 Pro by default, with automatic fallback if Pro is unavailable.

| Variable | Default | What it controls |
| --- | --- | --- |
| `GEMINI_MODEL` | `gemini-2.5-pro` | Primary model for all generation. |
| `GEMINI_REASONING_MODEL` | `gemini-2.5-pro` | Model for reasoning-flagged calls (outreach personalization, postcards, blogs, image prompts). Kept separate so you can ever dial `GEMINI_MODEL` down to Flash for bulk without losing Pro on reasoning. |
| `GEMINI_FALLBACK_MODEL` | `gemini-2.5-flash` | Graceful-degradation model. If the primary 429s (quota exhausted, billing not enabled, or a temporary quota blip), we fall back to this one with a visible log line. Set to `none` to disable and surface the 429. |

**Billing note:** Free-tier API keys get **0 daily Pro requests**. Enable billing
on the Google Cloud project tied to your API key to actually use 2.5 Pro. Until
you do, every call silently falls back to Flash.

## Vertex AI routing (recommended for production rendering)

AI Studio is the fastest path to draft text, but its free tier caps paid
Imagen at a low quota. **Vertex AI** is the same models through Google
Cloud billing — separate quota pool, no free-tier ceiling, and a production
path for image + text rendering at scale.

MaRe supports both backends from the same codebase. Text generation stays on
AI Studio (cheap, fast, enough quota once you enable billing). Image and video
rendering can be flipped to Vertex per-call (`--use-vertex` on
`mare content render-images`) or globally (`USE_VERTEX_FOR_IMAGES=true`).

### One-time setup

1. **Pick or create a GCP project** with billing attached. The project id is
   what goes into `VERTEX_PROJECT` below.
2. **Enable the Vertex AI API** on that project:

   ```bash
   gcloud services enable aiplatform.googleapis.com --project <your-project-id>
   ```

3. **Authenticate your machine** with Application Default Credentials (one-time,
   opens a browser):

   ```bash
   gcloud auth application-default login
   ```

4. **Add to `.env`:**

   ```
   VERTEX_PROJECT=your-gcp-project-id
   VERTEX_LOCATION=us-central1
   USE_VERTEX_FOR_IMAGES=true          # image rendering via Vertex
   USE_VERTEX_FOR_TEXT=true            # text generation via Vertex
   ```

5. **Probe it** (costs ~$0.02 — one fast Imagen render):

   ```bash
   python backend/scripts/probe_vertex.py
   ```

   You want to see `=== SUCCESS === Wrote artifacts/_probe/vertex_probe.png`.
   Any other verdict prints the exact next command to run.

### What flips when

| Env flag | Effect |
| --- | --- |
| `USE_VERTEX_FOR_IMAGES=true` | `mare content render-images` routes Imagen 4 through Vertex. CLI can override per-call with `--use-ai-studio` / `--use-vertex`. |
| `USE_VERTEX_FOR_TEXT=true` | All text generators (shorts, blogs, social, outreach, postcards) route through Vertex. |
| (All off) | Everything stays on the AI Studio key — zero setup, free-tier limits apply. |

Run `python -m mare content vertex-status` any time to see the current routing
at a glance.

## Status

- [x] Repo scaffold, brand module (voice, lingo, products, vocabulary, red flags)
- [x] Gemini client with dual-model routing + schema-validated structured outputs
- [x] Automatic 429 fallback + transient 503 retry
- [x] Pillar 2 — outreach email + LinkedIn DM
- [x] Pillar 2 — **hyper-personalized** outreach via social highlights
- [x] Pillar 2 — luxury direct-mail postcard concepts (front image + back copy)
- [x] Pillar 3 — Shorts, blogs, social captions (with AI-search blocks)
- [x] Pillar 3 — per-beat image prompts (Midjourney / Imagen / generic)
- [x] Pillar 3 — real image rendering via **Imagen 4** (`mare content render-images`)
- [x] Pillar 3 — HeyGen v2 job-spec adapter (dry-run; wire key to go live)
- [x] **LangGraph HITL approval workflow** (`mare workflow submit-*` / `mare review *`)
- [x] Durable SQLite state — drafts wait for review across sessions
- [x] Revision loop with reviewer notes baked back into the regeneration prompt
- [x] "MaRe Verified" stamped artifacts with YAML frontmatter (reviewer, ts, iters)
- [x] Official Brand Kit transcribed into `mare.brand.identity` (palette, typography, tone matrix, logo rules)
- [x] Mobile-first channel matrix (`mare.content.channels`) wired into image prompts + Imagen 4 renderer + CLI
- [ ] Pillar 1 — Revenue-verified salon prospecting data source
- [ ] Pillar 4 — AI-search rank tracker (is MaRe actually being cited?)
- [ ] Real salon social-highlight ingestion (currently manual via `--highlight`)
- [ ] Next.js review dashboard (shipping CLI first; dashboard is the same graph)
