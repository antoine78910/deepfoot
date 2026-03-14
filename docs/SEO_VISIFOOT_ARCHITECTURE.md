# SEO Architecture to Rank on "Visifoot" and AI Football Queries

## Goal

Deepfoot should not try to rank only on generic keywords like `football predictions` or `AI football predictions`.

It should build a full search architecture around:

- competitor intent: `visifoot`, `visifoot ai`, `visifoot alternative`, `visifoot vs deepfoot`
- product intent: `ai football predictions`, `football prediction ai`, `match prediction ai`
- transactional intent: `best football prediction ai`, `accurate football predictions today`
- programmatic intent: leagues, teams, match predictions, comparison pages
- AI citation intent: direct questions that ChatGPT, Perplexity, Claude, and Google AI Overviews can quote

The safest strategy is:

1. build Deepfoot as the clear category page for `AI football prediction`
2. create explicit comparison pages for competitor queries
3. create programmatic entity pages for leagues, teams, and matches
4. create answer-first content that AI systems can quote directly

Do not try to force `Visifoot` on the homepage or sitewide metadata. Use dedicated comparison and alternative pages instead.

## Current gaps in this repo

Based on the current frontend:

- the primary host is inconsistent: code uses `https://deepfoot.io` while SEO rules say `https://www.deepfoot.io`
- `robots.ts` is minimal and does not explicitly support AI crawler discoverability
- `sitemap.ts` is too small for a pSEO strategy and there is no visible `ai-sitemap`
- almost no page-level metadata is implemented
- no visible JSON-LD strategy exists yet
- the homepage is client-rendered, which is weaker for SEO than a server-rendered content-first homepage
- there are still several `Visifoot` strings in code/docs, which can confuse brand signals and entity understanding

## Target architecture

## 1. Brand and technical foundation

Canonical host:

- choose one host only
- recommended: `https://www.deepfoot.io` if that is the intended brand domain in your rules
- 301 redirect all variants to the canonical host
- use the same host in:
  - `frontend/app/layout.tsx`
  - `frontend/app/robots.ts`
  - `frontend/app/sitemap.ts`
  - Open Graph metadata
  - structured data

Core technical layer to add:

- `frontend/lib/seo/site.ts`
  - canonical host
  - brand name
  - default title patterns
  - social image paths

- `frontend/lib/seo/metadata.ts`
  - helper to generate page metadata
  - title
  - description
  - canonical
  - OG
  - Twitter

- `frontend/lib/seo/schema.ts`
  - `Organization`
  - `WebSite`
  - `FAQPage`
  - `Article`
  - `SportsEvent`
  - `BreadcrumbList`
  - `ItemList`

- `frontend/app/ai-sitemap.ts`
  - sitemap specifically listing homepage, comparison pages, methodology pages, important league pages, key prediction pages

## 2. Content architecture

You need 5 SEO layers.

### Layer A: Money pages

Pages that should rank first for product intent:

- `/ai-football-predictions`
- `/football-predictions-today`
- `/best-football-prediction-ai`
- `/match-prediction-ai`
- `/football-betting-analysis-ai`

Each page should answer:

- what Deepfoot is
- what predictions it provides
- which leagues it covers
- how the model works
- how probabilities are expressed
- why it is better than rule-based tipster sites

### Layer B: Competitor / alternative pages

This is where you target `Visifoot`.

Recommended pages:

- `/compare/deepfoot-vs-visifoot`
- `/alternatives/visifoot-alternative`
- `/compare/deepfoot-vs-forebet`
- `/compare/deepfoot-vs-fivethirtyeight`

Each competitor page should include:

- feature comparison table
- model explanation
- data freshness comparison
- supported prediction types
- pros / cons
- when to use each tool
- explicit answer to: "What is the best alternative to Visifoot?"

Important:

- stay factual
- avoid brand stuffing
- avoid misleading claims
- use comparison intent, not imitation intent

### Layer C: Programmatic entity pages

This is the scalable pSEO layer.

Recommended routes:

- `/predictions/[league]/[teamA]-vs-[teamB]`
- `/teams/[team]`
- `/leagues/[league]`

Page purpose:

- match page = rank on specific fixture intent
- team page = rank on branded team + prediction / stats / AI analysis intent
- league page = capture broad league intent and internally distribute authority

### Layer D: AI citation pages

These pages are designed for LLM retrieval, not only Google blue links.

Recommended pages:

- `/how-ai-football-predictions-work`
- `/how-accurate-are-ai-football-predictions`
- `/what-data-is-used-to-predict-football-matches`
- `/can-ai-predict-football-matches`
- `/deepfoot-methodology`

These pages should be:

- explicit
- answer-first
- short paragraphs
- bullet-heavy
- table-heavy
- FAQ-rich

### Layer E: Topical support cluster

Recommended support pages:

- `/premier-league-predictions`
- `/champions-league-predictions`
- `/la-liga-predictions`
- `/serie-a-predictions`
- `/bundesliga-predictions`

These should act as hybrid editorial + programmatic hubs that link to team and match pages.

## 3. Recommended page templates

## Homepage

The homepage should become the category-definition page for the entity:

- H1: `AI Football Predictions`
- H2 blocks:
  - what Deepfoot does
  - leagues covered
  - prediction types
  - how the model works
  - example probabilities
  - FAQ

The current homepage is visually strong, but it should become much more explicit for both Google and LLMs.

It should literally say:

- Deepfoot is an AI football match prediction platform
- it predicts 1X2, over/under, BTTS, exact score, and match scenarios
- it covers named leagues
- predictions are probabilities, not guarantees

## Comparison page template

Use this structure:

1. short answer summary
2. feature comparison table
3. data sources and methodology
4. prediction outputs
5. where Deepfoot is better
6. where the competitor may still be useful
7. FAQ

This is the best place to rank on:

- `visifoot alternative`
- `visifoot ai`
- `deepfoot vs visifoot`
- `sites like visifoot`

## Match page template

Mandatory blocks:

- unique title
- unique intro
- match overview
- team form
- key stats
- predicted probabilities
- explanation of the probabilities
- related league and team links
- FAQ
- `SportsEvent` schema

Do not index a match page unless it has enough unique data.

## Team page template

Mandatory blocks:

- team overview
- recent form
- average goals / xG / defensive record
- upcoming fixtures
- most likely next outcomes
- related prediction pages
- FAQ

## League page template

Mandatory blocks:

- league overview
- latest trends
- most predicted matches
- teams to watch
- internal links to team and match pages
- FAQ

## 4. AI SEO rules to apply

Your `aiseo.md` rule is correct: AI systems only recommend what is explicitly written.

So every important claim must be stated clearly in plain text:

- which leagues are covered
- which prediction outputs are available
- what data is used
- how probabilities are computed at a high level
- when the model updates
- who the product is for

AI-friendly formatting rules:

- answer the question in the first 1 to 3 sentences
- use short paragraphs
- use flat bullet lists
- use tables when comparing tools or outputs
- add FAQ on all strategic pages
- include definitions, not only slogans
- repeat the core entity in natural language:
  - `AI football prediction platform`
  - `football match predictor`
  - `AI football analysis tool`

## 5. Programmatic SEO rules to apply

Only index pages that pass a quality threshold.

Indexable:

- rich match pages with actual stats, form, odds context, and unique probability output
- team pages with recent form and future fixtures
- league hubs with enough unique commentary and internal links

Do not index:

- empty fixtures
- near-duplicate team aliases
- placeholder pages with only names swapped
- filtered URLs
- thin pages with no usable data

Quality gates for pSEO:

- unique title
- unique description
- one H1
- minimum 2 to 3 unique data blocks
- at least 5 to 8 internal links
- schema present
- canonical present
- index only when data freshness is valid

## 6. Internal linking system

You need a deliberate link graph.

Homepage links to:

- money pages
- methodology page
- top leagues
- top comparison pages

League pages link to:

- team pages
- match pages
- money pages

Team pages link to:

- upcoming match pages
- league page
- methodology page when relevant

Match pages link to:

- both team pages
- league page
- comparison or methodology pages only when contextually relevant

Competitor pages link to:

- the main money page
- methodology page
- pricing or analysis entry point

## 7. Schema architecture

Add these schemas consistently:

- global in `layout.tsx`
  - `Organization`
  - `WebSite`

- homepage
  - `FAQPage`
  - optional `SoftwareApplication`

- comparison pages
  - `FAQPage`
  - `BreadcrumbList`

- blog / methodology pages
  - `Article`
  - `FAQPage`

- prediction pages
  - `SportsEvent`
  - `BreadcrumbList`

For AI visibility, schema is not enough by itself, but it helps entity clarity and retrieval.

## 8. Metadata architecture

Every important page should implement `generateMetadata()`.

Rules:

- write explicit titles, not generic branding
- include the query intent in the title
- descriptions must clearly state value and coverage
- set canonical on every page
- create strong OG titles for shareability

Examples:

- `Deepfoot vs Visifoot: Which AI Football Predictor Is Better?`
- `AI Football Predictions Today: Match Probabilities and Analysis`
- `Premier League Predictions: AI Match Analysis and Probabilities`

## 9. Fastest wins for ranking on "Visifoot"

Priority order:

1. publish `/compare/deepfoot-vs-visifoot`
2. publish `/alternatives/visifoot-alternative`
3. remove or rework leftover internal `Visifoot` branding in user-facing code and metadata
4. strengthen homepage language around `AI football prediction platform`
5. add methodology and FAQ pages that LLMs can quote

Why:

- competitor keywords are easier to capture with dedicated pages than with homepage optimization
- LLMs like explicit comparisons
- Google can rank comparison pages faster than large pSEO sections if intent is clear

## 10. Suggested implementation roadmap

### Sprint 1: Technical SEO foundation

- unify canonical host
- create metadata helpers
- create schema helpers
- expand robots
- add `ai-sitemap`
- add canonical tags everywhere

### Sprint 2: High-intent editorial pages

- homepage rewrite for explicit category fit
- methodology page
- `AI football predictions` money page
- `football predictions today` page

### Sprint 3: Competitor capture

- `deepfoot-vs-visifoot`
- `visifoot-alternative`
- `deepfoot-vs-forebet`

### Sprint 4: Programmatic SEO

- league pages
- team pages
- match prediction pages
- sitemap segmentation
- freshness and deindex logic for thin pages

### Sprint 5: AI SEO reinforcement

- FAQ expansion
- quote-friendly summaries
- tables and definitions
- evidence blocks with probabilities, leagues, and model scope

## 11. Concrete content angles to win

Use these themes repeatedly:

- probabilities instead of generic tips
- data-driven football analysis
- AI match prediction methodology
- league coverage breadth
- scenario analysis, not only 1X2
- transparent model outputs

Good comparison angle against Visifoot:

- `Deepfoot focuses on explicit probability outputs, richer scenario analysis, and transparent match reasoning.`

Do not claim superiority without evidence. Support claims with:

- prediction types
- freshness
- coverage
- UX differences
- methodology differences

## 12. My recommendation for this project

If the goal is to rank fastest on `visifoot` and `visifoot ai`, the best architecture is:

1. keep the homepage focused on category terms, not the competitor brand
2. build a strong comparison cluster for `Visifoot`
3. build pSEO on leagues, teams, and predictions
4. build AI-citable methodology pages
5. fix the technical inconsistencies before scaling content

Without those foundations, programmatic SEO will scale indexable URLs but not authority.

## Next files to create in code

Recommended first implementation targets:

- `frontend/lib/seo/site.ts`
- `frontend/lib/seo/metadata.ts`
- `frontend/lib/seo/schema.ts`
- `frontend/app/ai-sitemap.ts`
- `frontend/app/compare/deepfoot-vs-visifoot/page.tsx`
- `frontend/app/alternatives/visifoot-alternative/page.tsx`
- `frontend/app/how-ai-football-predictions-work/page.tsx`
- `frontend/app/ai-football-predictions/page.tsx`

## Success metrics

Track these in Search Console and analytics:

- impressions on `visifoot` and `visifoot ai`
- impressions on `ai football predictions`
- indexed count of league / team / match pages
- clicks from comparison pages
- citations or referrals from AI tools when measurable
- branded search growth for `Deepfoot`
