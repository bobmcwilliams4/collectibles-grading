# Collectibles Grading System

An AI-powered comic book grading application with multi-model consensus voting, real-time webcam capture, and automated pricing aggregation.

## Features

### AI Consensus Grading
- **5 AI Providers**: Claude, Gemini, OpenRouter, HuggingFace, Local LLMs (Ollama/LM Studio)
- **Weighted Voting**: Claude (35%), Gemini (25%), OpenRouter (20%), HuggingFace (15%), Local (5%)
- **85% Agreement Threshold**: Ensures high-confidence grades
- **Defect Confirmation**: Requires 2+ models to confirm each defect
- **Front/Back Analysis**: 70%/30% weighted cover analysis

### Multi-Source Pricing
- **GoCollect/GPA**: Professional grading analytics
- **Heritage Auctions**: Auction house sales data
- **eBay Sold Listings**: Real-time market prices
- **Price Aggregation**: Weighted average with outlier removal

### Real-Time Webcam Capture
- **Auto Border Detection**: OpenCV-based comic detection
- **Quality Scoring**: Sharpness, focus, brightness, contrast analysis
- **Auto-Capture**: Smart snapshot timing when stable
- **Voice Feedback**: Text-to-speech guidance

### Desktop Application
- **Electron App**: Cross-platform desktop interface
- **Live Camera Preview**: Real-time webcam feed
- **Batch Processing**: Grade multiple comics at once
- **WebSocket Updates**: Live grading progress

### Static Investor Portal
- **Netlify Deployment**: One-click static export
- **Gallery View**: Browse entire collection
- **Statistics Dashboard**: Collection analytics
- **Mobile Responsive**: Works on all devices

### Promethian Vault Integration
- **Pentagon-Level Security**: AES-256-GCM + RSA-4096 encryption
- **Automatic Key Retrieval**: API keys loaded securely from vault
- **245+ Secrets**: Access to full ECHO PRIME key inventory
- **Fallback Support**: Environment variables if vault unavailable

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ (for Electron app)
- Webcam (for capture features)

### Python Setup
```bash
cd X:\ECHO_PRIME\COLLECTIBLES_GRADING
pip install -r requirements.txt
```

### Node.js Setup (Electron App)
```bash
cd electron-app
npm install
```

### Configuration

#### Option 1: Promethian Vault (Recommended)
The system automatically retrieves API keys from the Promethian Vault at:
```
Vault: X:\ECHO_PRIME\PROMETHEUS_PRIME\.promethian_vault\vault.db
Password: X:\ECHO_PRIME\PROMETHEUS_PRIME\.env (VAULT_MASTER_PASSWORD)
```

No manual configuration needed - keys are loaded on startup.

#### Option 2: Environment Variables (Fallback)
```bash
set ANTHROPIC_API_KEY=your_key_here
set GOOGLE_API_KEY=your_key_here
set OPENROUTER_API_KEY=your_key_here
set HUGGINGFACE_API_KEY=your_key_here
```

#### Option 3: Config File
Edit `config/ai_config.json` with your API keys (not recommended for production).

## Usage

### Start Backend Server
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Electron App
```bash
cd electron-app
npm start
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/comics` | GET | List all comics |
| `/comics` | POST | Add new comic |
| `/comics/{id}` | GET | Get comic details |
| `/grade/{id}` | POST | Grade a comic |
| `/grade/batch` | POST | Batch grade comics |
| `/price/{id}` | POST | Get pricing data |
| `/review/pending` | GET | Comics needing review |
| `/export` | POST | Export collection |
| `/stats` | GET | Collection statistics |
| `/vault/status` | GET | Promethian Vault status |
| `/vault/providers` | GET | Configured AI providers |
| `/vault/reload` | POST | Reload vault configuration |

### WebSocket Events

Connect to `ws://localhost:8000/ws/{client_id}` for real-time updates:

- `grade_complete`: Grading finished
- `price_update`: New pricing data
- `batch_progress`: Batch job progress
- `error`: Error notification

## Project Structure

```
COLLECTIBLES_GRADING/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── models.py            # Pydantic models
│   ├── database.py          # SQLite operations
│   ├── ai_consensus.py      # AI orchestration
│   ├── pricing_engine.py    # Price aggregation
│   ├── image_processor.py   # Image analysis
│   ├── batch_processor.py   # Batch operations
│   ├── analytics.py         # Statistics engine
│   ├── cache_manager.py     # Multi-level caching
│   ├── logging_config.py    # Logging system
│   ├── oauth_manager.py     # Token management
│   └── claude_code_integration.py
├── ai_providers/
│   ├── claude_grader.py     # Claude API
│   ├── gemini_grader.py     # Google Gemini
│   ├── openrouter_grader.py # OpenRouter
│   ├── huggingface_grader.py
│   ├── local_llm_grader.py  # Ollama/LM Studio
│   └── consensus_calculator.py
├── pricing_sources/
│   ├── gpa_scraper.py       # GoCollect
│   ├── heritage_scraper.py  # Heritage Auctions
│   └── ebay_scraper.py      # eBay sold listings
├── webcam_module/
│   ├── camera_manager.py    # Camera control
│   ├── border_detector.py   # Comic detection
│   ├── quality_scorer.py    # Image quality
│   ├── auto_capture.py      # Smart capture
│   └── voice_feedback.py    # TTS feedback
├── electron-app/
│   ├── main.js              # Electron main
│   ├── preload.js           # IPC bridge
│   ├── renderer/
│   │   ├── index.html       # Main UI
│   │   └── app.js           # App logic
│   └── styles/
│       └── main.css         # Dark theme
├── static_export/
│   ├── generate_portal.py   # HTML generator
│   └── templates/           # Jinja2 templates
├── config/
│   ├── ai_config.json       # API settings
│   ├── grading_standards.json # CGC criteria
│   └── camera_config.json   # Webcam settings
└── data/
    ├── database/            # SQLite files
    ├── images/              # Captured images
    ├── exports/             # Static exports
    └── cache/               # Cache files
```

## CGC Grading Scale

| Grade | Label | Description |
|-------|-------|-------------|
| 10.0 | Gem Mint | Perfect in every way |
| 9.8 | Near Mint/Mint | Nearly perfect with minor defects |
| 9.4 | Near Mint | Several minor defects acceptable |
| 8.0 | Very Fine | Moderate wear, still attractive |
| 6.0 | Fine | Slightly above average |
| 4.0 | Very Good | Significant wear visible |
| 2.0 | Good | Substantial wear |
| 0.5 | Poor | Barely readable |

## Defect Detection

The system detects and grades these defect types:

- **Spine**: Stress lines, roll, splits
- **Cover**: Tears, creases, detachment
- **Edges**: Wear, chipping, foxing
- **Corners**: Blunting, creases
- **Color**: Fading, oxidation
- **Staples**: Rust, loose, missing
- **Contamination**: Writing, tape, stains

## Batch Processing

```python
# Example batch import from directory
from backend.batch_processor import BatchImporter, BatchProcessor

items = await BatchImporter.from_directory(
    "path/to/comics",
    pattern="*_front.*"
)

processor = BatchProcessor(grader_func)
job = await processor.create_batch("My Batch", items, concurrency=3)
await processor.start_batch(job.id)
```

## Analytics

The analytics engine provides:

- Grade distribution charts
- Value tracking over time
- Publisher statistics
- Era breakdown (Golden, Silver, Bronze, etc.)
- Defect frequency analysis
- AI provider performance metrics
- ROI calculations

## Static Export

Generate a static website for your collection:

```python
from static_export.generate_portal import PortalGenerator

generator = PortalGenerator(
    output_dir="./exports/my_collection",
    title="My Comic Collection"
)
generator.generate(comics)
```

Deploy to Netlify by dragging the output folder to netlify.com.

## Development

### Running Tests
```bash
pytest tests/ -v --cov=backend
```

### Code Formatting
```bash
black backend/ ai_providers/ pricing_sources/
isort backend/ ai_providers/ pricing_sources/
```

### Type Checking
```bash
mypy backend/
```

## Promethian Vault Integration

The system integrates with the ECHO PRIME Promethian Vault for secure API key management.

### How It Works

1. **Automatic Key Retrieval**: On startup, the server connects to the Promethian Vault and loads all required API keys.

2. **Priority Order**:
   - First: Promethian Vault (most secure)
   - Second: Environment variables
   - Third: Local config file (not recommended)

3. **Available Keys in Vault**:
   ```python
   # AI Providers
   ANTHROPIC_API_KEY_api_key
   GOOGLE_API_KEY_api_key
   OPENROUTER_API_KEY_api_key
   HUGGINGFACE_API_KEY_api_key
   GROQ_API_KEY_api_key

   # Pricing Sources
   GOCOLLECT_API_KEY_api_key
   HERITAGE_API_KEY_api_key
   EBAY_API_KEY_api_key
   ```

### Vault API Endpoints

```python
# Check vault status
GET /vault/status

# List configured providers
GET /vault/providers

# Reload configuration from vault
POST /vault/reload
```

### Manual Vault Access

```python
from backend.vault_integration import get_vault, get_api_key

# Get vault instance
vault = get_vault()

# Get specific key
anthropic_key = get_api_key('ANTHROPIC_API_KEY')

# Check vault status
status = vault.get_vault_status()
print(f"Vault connected: {status['available']}")
print(f"Secrets available: {status.get('total_secrets', 0)}")
```

## API Keys Required

| Provider | Vault Key | Environment Variable | Get Key |
|----------|-----------|---------------------|---------|
| Anthropic (Claude) | `ANTHROPIC_API_KEY_api_key` | `ANTHROPIC_API_KEY` | console.anthropic.com |
| Google (Gemini) | `GOOGLE_API_KEY_api_key` | `GOOGLE_API_KEY` | ai.google.dev |
| OpenRouter | `OPENROUTER_API_KEY_api_key` | `OPENROUTER_API_KEY` | openrouter.ai |
| HuggingFace | `HUGGINGFACE_API_KEY_api_key` | `HUGGINGFACE_API_KEY` | huggingface.co |
| eBay | `EBAY_API_KEY_api_key` | `EBAY_API_KEY` | developer.ebay.com |

## Local LLM Support

For offline grading using local models:

### Ollama Setup
```bash
# Install Ollama
ollama pull llava:13b

# Start server (default: localhost:11434)
ollama serve
```

### LM Studio Setup
1. Download LM Studio from lmstudio.ai
2. Load a vision model (e.g., LLaVA)
3. Start local server on port 1234

## License

MIT License - see LICENSE file for details.

## Support

For issues and feature requests, please open a GitHub issue.
