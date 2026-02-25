<p align="center">
  <h1 align="center">EPOCGS - Echo Prime Omega Collectibles Grading System</h1>
  <p align="center">
    AI-powered multi-model consensus grading for collectibles. Comics, trading cards, coins, stamps, vinyl, action figures, and video games -- graded by 15+ AI providers with real-time webcam capture, automated pricing, and professional cataloging.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/FastAPI-latest-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Electron-desktop-47848F?logo=electron&logoColor=white" alt="Electron">
  <img src="https://img.shields.io/badge/Expo-iOS_app-000020?logo=expo&logoColor=white" alt="Expo">
  <img src="https://img.shields.io/badge/Next.js-website-black?logo=next.js&logoColor=white" alt="Next.js">
  <img src="https://img.shields.io/badge/AI_Providers-15+-orange" alt="15+ AI Providers">
  <img src="https://img.shields.io/badge/lines-77%2C800+-purple" alt="77,800+ lines">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

---

## Overview

EPOCGS is a comprehensive collectibles grading platform that uses multi-AI consensus voting to produce professional-grade assessments. The system captures items via webcam or uploaded images, runs them through up to 15 AI vision models simultaneously, applies weighted consensus with defect confirmation thresholds, and produces grades aligned with industry standards (CGC for comics, PSA/BGS for cards, NGC/PCGS for coins, etc.). Integrated pricing aggregation pulls real-time market data from GoCollect, Heritage Auctions, eBay, and CGC Census.

The platform ships as a FastAPI backend, an Electron desktop app, an Expo/React Native iOS app, and a Next.js marketing and marketplace website.

---

## Architecture

```
collectibles-grading/
+-- backend/                          # FastAPI backend (core)
|   +-- main.py                      # App factory, 50+ endpoints
|   +-- models.py                    # Pydantic models
|   +-- database.py                  # SQLite async via SQLAlchemy
|   +-- database_v2.py              # V2 schema with expanded fields
|   +-- ai_consensus.py             # Multi-AI orchestration engine
|   +-- pricing_engine.py           # Multi-source price aggregation
|   +-- image_processor.py          # Image analysis and enhancement
|   +-- image_processor_v2.py       # V2 with advanced defect detection
|   +-- batch_processor.py          # Batch grading job queue
|   +-- analytics.py                # Collection statistics engine
|   +-- cache_manager.py            # Multi-level caching (memory + disk)
|   +-- era_grading.py              # Era-specific grading standards
|   +-- security.py                 # Auth, rate limiting, audit logging
|   +-- auth_routes.py              # Authentication endpoints
|   +-- parallel_grading.py         # Concurrent multi-model execution
|   +-- professional_features.py    # Pro tier features
|   +-- price_research.py           # Deep pricing research
|   +-- price_updater.py            # Background price refresh
|   +-- catalog_export.py           # Collection export (PDF, CSV, JSON)
|   +-- cgc_integration.py          # CGC submission portal integration
|   +-- metrics.py                  # Performance metrics
|   +-- provider_health.py          # AI provider health monitoring
|   +-- resource_allocator.py       # GPU/CPU resource management
|   +-- ai_providers/                # 15+ AI grading providers
|   |   +-- universal_grader.py     # Universal multi-type grading engine
|   |   +-- claude_grader.py        # Anthropic Claude (35% weight)
|   |   +-- gemini_grader.py        # Google Gemini (25% weight)
|   |   +-- openrouter_grader.py    # OpenRouter models (20% weight)
|   |   +-- groq_grader.py          # Groq (Llama vision)
|   |   +-- grok_grader.py          # xAI Grok
|   |   +-- deepseek_grader.py      # DeepSeek
|   |   +-- huggingface_grader.py   # HuggingFace models
|   |   +-- ollama_vision_grader.py # Ollama local models
|   |   +-- openai_grader.py        # OpenAI GPT-4V
|   |   +-- cloudflare_grader.py    # Cloudflare Workers AI
|   |   +-- sambanova_grader.py     # SambaNova
|   |   +-- hyperbolic_grader.py    # Hyperbolic
|   |   +-- together_grader.py      # Together AI
|   |   +-- cohere_research.py      # Cohere (research enrichment)
|   |   +-- perplexity_research.py  # Perplexity (market research)
|   |   +-- fallback_providers.py   # Failover chain
|   |   +-- batch_grader.py         # Batch multi-model execution
|   |   +-- swarm_brain.py          # Swarm intelligence aggregation
|   |   +-- tts_providers.py        # Voice feedback (ElevenLabs, Cartesia)
|   +-- pricing_sources/
|   |   +-- gpa_scraper.py          # GoCollect/GPA Analytics
|   |   +-- heritage_scraper.py     # Heritage Auctions
|   |   +-- ebay_scraper.py         # eBay sold listings
|   |   +-- cgc_lookup.py           # CGC Census lookup
|   |   +-- comic_vine_lookup.py    # ComicVine metadata
+-- webcam_module/                   # Real-time capture system
|   +-- camera_manager.py           # Camera device control
|   +-- border_detector.py          # OpenCV border detection
|   +-- quality_scorer.py           # Sharpness, focus, exposure analysis
|   +-- auto_capture.py             # Smart capture timing
|   +-- voice_feedback.py           # TTS guidance during capture
+-- electron-app/                    # Desktop application
|   +-- main.js                     # Electron main process
|   +-- preload.js                  # Secure IPC bridge
|   +-- renderer/
|       +-- app.js                  # Application logic
|       +-- service-worker.js       # Offline support
+-- ios-app/                        # React Native / Expo iOS app
|   +-- app/
|   |   +-- (tabs)/                 # Tab navigation
|   |   |   +-- index.tsx           # Home dashboard
|   |   |   +-- grade.tsx           # Camera grading screen
|   |   |   +-- catalog.tsx         # Collection catalog
|   |   |   +-- marketplace.tsx     # Buy/sell marketplace
|   |   |   +-- settings.tsx        # App settings
|   |   +-- camera.tsx              # Full camera screen
|   |   +-- collection.tsx          # Collection details
|   |   +-- comic/[id].tsx          # Individual item view
|   |   +-- grade-result.tsx        # Grading results
|   |   +-- login.tsx               # Authentication
|   +-- components/
|   |   +-- ARPreview.tsx           # AR-powered item preview
|   |   +-- MatrixRain.tsx          # Animated background
|   |   +-- SwipeableCard.tsx       # Swipeable item cards
|   |   +-- StatisticsDashboard.tsx # Collection analytics
|   +-- lib/
|   |   +-- api.ts                  # Backend API client
|   |   +-- barcodeService.ts       # Barcode/UPC scanning
|   |   +-- gradingService.ts       # Grading API integration
|   |   +-- firebase.ts             # Firebase integration
|   |   +-- imageCache.ts           # Image caching layer
|   |   +-- offlineStorage.ts       # Offline data persistence
|   |   +-- priceTracking.ts        # Price tracking alerts
|   |   +-- ttsService.ts           # Voice feedback
|   +-- functions/                   # Firebase Cloud Functions
|       +-- src/index.ts            # Serverless grading functions
+-- website/                        # Next.js marketing site
|   +-- app/
|   |   +-- page.tsx                # Landing page
|   |   +-- collection/page.tsx     # Collection showcase
|   |   +-- marketplace/page.tsx    # Marketplace
|   |   +-- services/page.tsx       # Service descriptions
|   |   +-- showcase/page.tsx       # Featured items
|   |   +-- download/page.tsx       # App downloads
|   |   +-- api/stripe/             # Stripe payment endpoints
|   |   +-- api/offers/             # Offer management API
|   +-- lib/
|       +-- stripe.ts               # Stripe integration
|       +-- firebase.ts             # Firebase client
|       +-- echo-prime.ts           # Echo Prime integration
+-- config/                         # Grading standards (JSON)
|   +-- grading_standards.json      # CGC comic grading
|   +-- trading_cards_grading_standards.json  # PSA/BGS
|   +-- coins_grading_standards.json          # NGC/PCGS
|   +-- stamps_grading_standards.json         # Scott catalog
|   +-- vinyl_grading_standards.json          # Goldmine/VG+
|   +-- action_figures_grading_standards.json # AFA
|   +-- video_games_grading_standards.json    # VGA/WATA
|   +-- era_grading_prompts.json    # Era-specific prompts
|   +-- catalog_templates.json      # Export templates
|   +-- camera_config.json          # Webcam settings
+-- launcher/                       # System launcher
+-- scripts/                        # Utility scripts
+-- skills/                         # AI skill definitions
```

---

## Supported Collectible Types

| Type | Grading Scale | Standard Body | Grades |
|------|---------------|---------------|--------|
| Comics | 0.5 - 10.0 | CGC | 25 grade points (Poor to Gem Mint) |
| Trading Cards | 1 - 10 | PSA / BGS | Gem Mint, Mint, NM-MT, etc. |
| Coins | 1 - 70 | NGC / PCGS | Sheldon scale (Poor to MS-70) |
| Stamps | 1 - 100 | PSE / Scott | Superb to Poor |
| Vinyl Records | M to P | Goldmine | Mint, NM, VG+, VG, G+, G, F, P |
| Action Figures | 0 - 100 | AFA | C-Scale (packaging + figure) |
| Video Games | 1 - 100 | VGA / WATA | Seal grade + cart/disc grade |

---

## AI Consensus System

### Provider Weights (Comics)

| Provider | Weight | Model |
|----------|--------|-------|
| Claude | 35% | claude-3.5-sonnet (vision) |
| Gemini | 25% | gemini-1.5-pro (vision) |
| OpenRouter | 20% | Multiple vision models |
| HuggingFace | 15% | Open source vision |
| Local (Ollama) | 5% | LLaVA 13B |

### Consensus Rules
- **85% agreement threshold** for final grade confirmation
- **Defect confirmation** requires 2+ models to flag each defect
- **Front/back weighting**: 70% cover / 30% back analysis
- **Outlier removal**: Grades beyond 2 standard deviations are excluded
- **Confidence scoring**: Each model reports confidence (0-1), weighted into final score

### Defect Detection Categories

| Category | Defects Detected |
|----------|------------------|
| Spine | Stress lines, roll, splits, ticks |
| Cover | Tears, creases, detachment, foxing |
| Edges | Wear, chipping, browning |
| Corners | Blunting, dog ears, creases |
| Color | Fading, oxidation, sun damage |
| Staples | Rust, loose, missing, migrated |
| Contamination | Writing, tape, stains, labels |

---

## Multi-Source Pricing

| Source | Data Type | Method |
|--------|-----------|--------|
| GoCollect / GPA | Professional analytics | API + scraping |
| Heritage Auctions | Auction results | Scraping |
| eBay Sold Listings | Real-time market | Sold item scraping |
| CGC Census | Population report | CGC API |
| ComicVine | Metadata enrichment | API |

Price aggregation uses weighted averages with outlier removal for accurate fair market value estimation.

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/comics` | List all items in collection |
| POST | `/comics` | Add new item |
| GET | `/comics/{id}` | Get item details |
| PUT | `/comics/{id}` | Update item |
| DELETE | `/comics/{id}` | Remove item |
| POST | `/grade/{id}` | Run AI consensus grading |
| POST | `/grade/batch` | Batch grade multiple items |
| POST | `/price/{id}` | Fetch pricing data |
| GET | `/review/pending` | Items needing human review |
| POST | `/export` | Export collection (PDF/CSV/JSON) |
| GET | `/stats` | Collection statistics |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/refresh` | Refresh token |
| GET | `/api/auth/me` | Current user profile |

### CGC Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/cgc/login` | Authenticate with CGC |
| GET | `/cgc/status` | CGC session status |
| GET | `/cgc/census/{title}` | Census population data |
| POST | `/cgc/verify/{id}` | Verify CGC certification |

### Vault and Provider Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/vault/status` | Credential vault status |
| GET | `/vault/providers` | List configured AI providers |
| POST | `/vault/reload` | Reload vault configuration |

### WebSocket Events

Connect to `ws://localhost:8000/ws/{client_id}`:

| Event | Payload |
|-------|---------|
| `grade_complete` | Final consensus grade + defect report |
| `price_update` | New pricing data for item |
| `batch_progress` | Batch job progress (n/total) |
| `voice_feedback` | TTS feedback message |
| `error` | Error notification |

---

## Platforms

| Platform | Technology | Status |
|----------|------------|--------|
| **Backend API** | Python, FastAPI, SQLite | Production |
| **Desktop App** | Electron | Production |
| **iOS App** | React Native, Expo | Beta |
| **Website** | Next.js, Vercel | Production |
| **Static Portal** | Jinja2 HTML export | Production |

---

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Desktop App
```bash
cd electron-app
npm install
npm start
```

### iOS App
```bash
cd ios-app
npm install
npx expo start
```

### Website
```bash
cd website
npm install
npm run dev
```

---

## Voice Feedback

The grading system provides real-time voice feedback during webcam capture and grading using two voice personality engines:

| Voice | Provider | Role |
|-------|----------|------|
| Bree | ElevenLabs | Warm, encouraging capture guidance |
| Raistlin | Cartesia | Analytical grading commentary |
| Collection Master | ElevenLabs | Portfolio analysis narration |

---

## Analytics

The analytics engine provides:

- Grade distribution histograms
- Collection value tracking over time
- Publisher and era breakdown (Golden, Silver, Bronze, Modern, etc.)
- Defect frequency analysis across collection
- AI provider accuracy and agreement metrics
- ROI calculations (purchase price vs. current market value)
- Rarity scoring based on CGC Census population

---

## License

MIT License. See LICENSE file for details.

## Part of Echo Omega Prime

Built by [Echo Prime Technologies](https://echo-ept.com) as part of the Echo Omega Prime autonomous AI platform.
