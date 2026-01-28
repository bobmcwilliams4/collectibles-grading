"""
FastAPI Backend Server for Comic Book Grading System
Complete REST API with WebSocket support for real-time grading
Enhanced with comprehensive security features
"""


# CRITICAL: Load .env FIRST before any other imports to override system env vars
import os
from pathlib import Path as _Path
try:
    from dotenv import dotenv_values
    _env_file = _Path(__file__).parent / ".env"
    if _env_file.exists():
        _config = dotenv_values(str(_env_file))
        for _key, _value in _config.items():
            if _value is not None:
                os.environ[_key] = _value
        print(f"[MAIN] Loaded {len(_config)} env vars from .env (override=True)")
except ImportError:
    print("[MAIN] dotenv not installed, using system env vars only")

import asyncio
import logging
import subprocess
import json
import re
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, UploadFile, File, Query, Depends, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn

# Security imports MUST come FIRST before vault_integration
# The vault initialization can corrupt sys.modules on Python 3.13+
# which causes subsequent imports to fail with KeyError
from security import (
    initialize_security, security_headers_middleware, audit_middleware,
    require_auth, require_grader, require_admin, check_rate_limit,
    input_validator, ALLOWED_ORIGINS, SECURITY_HEADERS,
    rate_limiter, audit_logger
)
from auth_routes import router as auth_router

from database import DatabaseManager, get_db
from models import (
    ComicCreate, ComicFull, ComicGradeRequest, ComicSearchQuery,
    BatchGradeRequest, BatchGradeResult, ExportRequest, SystemStats,
    APIResponse, ConsensusGrade, ConsensusPricing
)
from ai_consensus import ConsensusGrader
from pricing_engine import PricingEngine
from image_processor import ImageProcessor
# VAULT DISABLED - corrupts sys.modules on GS343 Gateway profile
# from vault_integration import get_vault, initialize_vault
from config_loader import get_config_loader, initialize_config
from cgc_integration import cgc_login, cgc_logout, cgc_status, cgc_verify, cgc_census
from grading_events import init_voice_triggers, init_both_voice_systems, VoicePersonality
from price_updater import (
    run_price_updates, get_price_scheduler_status, background_price_updater,
    price_scheduler, EbayPriceScraper, CGCPriceGuide
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/server.log') if os.environ.get('APP_ENV') == 'production' else logging.FileHandler('P:/SOVEREIGN_APPS/collectibles_grading_system/logs/server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# CGC Grading Scale
CGC_GRADES = {
    10.0: "Gem Mint", 9.9: "Mint", 9.8: "Near Mint/Mint",
    9.6: "Near Mint+", 9.4: "Near Mint", 9.2: "Near Mint-",
    9.0: "Very Fine/Near Mint", 8.5: "Very Fine+", 8.0: "Very Fine",
    7.5: "Very Fine-", 7.0: "Fine/Very Fine", 6.5: "Fine+",
    6.0: "Fine", 5.5: "Fine-", 5.0: "Very Good/Fine",
    4.5: "Very Good+", 4.0: "Very Good", 3.5: "Very Good-",
    3.0: "Good/Very Good", 2.5: "Good+", 2.0: "Good",
    1.8: "Good-", 1.5: "Fair/Good", 1.0: "Fair", 0.5: "Poor"
}

def get_grade_label(grade: float) -> str:
    """Get CGC grade label for a numeric grade"""
    closest = min(CGC_GRADES.keys(), key=lambda x: abs(x - grade))
    return CGC_GRADES[closest]

# Initialize components
db = DatabaseManager()
consensus_grader = ConsensusGrader()
pricing_engine = PricingEngine()
image_processor = ImageProcessor()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

ws_manager = ConnectionManager()


def refresh_claude_oauth_token():
    """
    Load Claude CLI OAuth token for voice feedback.
    
    Token sources (in priority order):
    1. X:\\ECHO_PRIME\\.claude_oauth_token (saved by setup script)
    2. ~/.claude/.credentials.json (Claude CLI credentials)
    3. CLAUDE_CODE_OAUTH_TOKEN environment variable
    
    NOTE: If token is expired, user must run 'claude /login' to re-authenticate.
    """
    # Source 1: Saved token file
    saved_token_path = Path(r"X:\ECHO_PRIME\.claude_oauth_token")
    if saved_token_path.exists():
        try:
            token = saved_token_path.read_text(encoding='utf-8-sig').strip()
            if token.startswith('sk-ant-oat'):
                os.environ['CLAUDE_CODE_OAUTH_TOKEN'] = token
                logger.info(f"Claude OAuth token loaded from saved file")
                return True
        except Exception as e:
            logger.warning(f"Failed to read saved token: {e}")
    
    # Source 2: Claude CLI credentials
    credentials_path = Path.home() / ".claude" / ".credentials.json"
    if credentials_path.exists():
        try:
            with open(credentials_path, 'r') as f:
                creds = json.load(f)
            
            oauth_data = creds.get('claudeAiOauth', {})
            access_token = oauth_data.get('accessToken')
            expires_at = oauth_data.get('expiresAt', 0)
            
            # Check expiration
            current_time_ms = int(time.time() * 1000)
            if current_time_ms > expires_at:
                logger.warning("Claude OAuth token EXPIRED. Run 'claude /login' to re-authenticate.")
                # Still set it - server-side validity may differ from local expiry
            
            if access_token:
                os.environ['CLAUDE_CODE_OAUTH_TOKEN'] = access_token
                logger.info("Claude OAuth token loaded from credentials file")
                return True
                
        except Exception as e:
            logger.warning(f"Failed to read Claude credentials: {e}")
    
    # Source 3: Environment variable
    if os.environ.get('CLAUDE_CODE_OAUTH_TOKEN'):
        logger.info("Claude OAuth token found in environment")
        return True
    
    logger.warning("No Claude OAuth token available - voice dialogue may not work")
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Comic Grading Server...")

    # Refresh Claude OAuth token if needed
    logger.info("Checking Claude OAuth token...")
    refresh_claude_oauth_token()

    # Initialize security module
    logger.info("Initializing security module...")
    await initialize_security()
    logger.info("Security module initialized")

    # Initialize Promethian Vault for secure API key access
    # DISABLED - Vault corrupts sys.warnoptions, breaking Python warnings module
    logger.info("Promethian Vault DISABLED - using environment variables for API keys")
    vault_available = False  # initialize_vault()
    # if vault_available:
    #     vault = get_vault()
    #     status = vault.get_vault_status()
    #     logger.info(f"Promethian Vault connected: {status.get('total_secrets', 0)} secrets available")
    # else:
    #     logger.warning("Promethian Vault not available - using environment variables for API keys")

    # Initialize configuration with vault integration
    config_loader = initialize_config()
    enabled_providers = config_loader.get_enabled_providers()
    logger.info(f"AI providers enabled: {', '.join(enabled_providers) if enabled_providers else 'None'}")

    # Initialize database
    db._init_database()

    # VOICE DISABLED - was causing double-speak issues
    # Voice feedback will be handled by frontend only
    logger.info("Voice feedback DISABLED (backend events caused double-speak)")
    # try:
    #     raistlin_triggers, bree_triggers = init_both_voice_systems(enabled=True)
    #     logger.info(f"Voice feedback initialized: RAISTLIN (grading) + BREE (commentary)")
    # except Exception as e:
    #     logger.warning(f"Voice feedback initialization failed: {e} - continuing without voice")

    # Ensure directories exist
    Path("P:/SOVEREIGN_APPS/collectibles_grading_system/images/captures").mkdir(parents=True, exist_ok=True)
    Path("P:/SOVEREIGN_APPS/collectibles_grading_system/logs").mkdir(parents=True, exist_ok=True)
    Path("P:/SOVEREIGN_APPS/collectibles_grading_system/cache").mkdir(parents=True, exist_ok=True)

    logger.info("Server initialized successfully")

    # Start background price updater task
    price_update_task = asyncio.create_task(background_price_updater())
    logger.info("Background price updater started (runs every 6 hours)")

    yield

    # Cancel background tasks on shutdown
    price_update_task.cancel()
    try:
        await price_update_task
    except asyncio.CancelledError:
        logger.info("Price updater task cancelled")

    # Cleanup
    logger.info("Shutting down server...")


# Create FastAPI app
app = FastAPI(
    title="Comic Book Grading System",
    description="AI-powered comic book grading with multi-model consensus",
    version="1.0.0",
    lifespan=lifespan
)

# Security middleware - TEMPORARILY DISABLED due to sniffio async conflict
# app.middleware("http")(security_headers_middleware)
# app.middleware("http")(audit_middleware)

# CORS middleware - restricted to allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
)

# Static files
app.mount("/images", StaticFiles(directory="P:/SOVEREIGN_APPS/collectibles_grading_system/images"), name="images")

# Include authentication routes
app.include_router(auth_router)


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/", response_model=APIResponse)
async def root():
    """API root endpoint"""
    return APIResponse(
        success=True,
        message="Comic Grading System API v1.0.0",
        data={"status": "operational"}
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": "operational",
            "ai_consensus": "operational",
            "pricing_engine": "operational"
        }
    }


@app.get("/ai/status")
async def ai_status_check():
    """Check AI provider connectivity and API key status"""
    providers = {}

    # Check Claude (Anthropic) - via OAuth or API key
    claude_status = "offline"
    claude_oauth = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    claude_api = os.getenv('ANTHROPIC_API_KEY')
    if claude_oauth or claude_api:
        claude_status = "ready"
    providers['claude'] = {
        'name': 'Claude',
        'status': claude_status,
        'icon': 'C',
        'color': '#D97706'
    }

    # Check Gemini (Google)
    gemini_status = "offline"
    gemini_key = os.getenv('GOOGLE_API_KEY')
    if gemini_key:
        gemini_status = "ready"
    providers['gemini'] = {
        'name': 'Gemini',
        'status': gemini_status,
        'icon': 'G',
        'color': '#4285F4'
    }

    # Check OpenRouter (Free tier access to multiple models)
    openrouter_status = "offline"
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    if openrouter_key:
        openrouter_status = "ready"
    providers['openrouter'] = {
        'name': 'OpenRouter',
        'status': openrouter_status,
        'icon': 'OR',
        'color': '#10B981'
    }

    # Check Groq (Fast inference)
    groq_status = "offline"
    groq_key = os.getenv('GROQ_API_KEY')
    if groq_key:
        groq_status = "ready"
    providers['groq'] = {
        'name': 'Groq',
        'status': groq_status,
        'icon': 'GQ',
        'color': '#F97316'
    }

    # Check DeepSeek
    deepseek_status = "offline"
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    if deepseek_key:
        deepseek_status = "ready"
    providers['deepseek'] = {
        'name': 'DeepSeek',
        'status': deepseek_status,
        'icon': 'DS',
        'color': '#3B82F6'
    }

    # Check Grok (xAI)
    grok_status = "offline"
    grok_key = os.getenv('XAI_API_KEY') or os.getenv('GROK_API_KEY')
    if grok_key:
        grok_status = "ready"
    providers['grok'] = {
        'name': 'Grok',
        'status': grok_status,
        'icon': 'GK',
        'color': '#8B5CF6'
    }

    # Check Perplexity (Research)
    perplexity_status = "offline"
    perplexity_key = os.getenv('PERPLEXITY_API_KEY')
    if perplexity_key:
        perplexity_status = "ready"
    providers['perplexity'] = {
        'name': 'Perplexity',
        'status': perplexity_status,
        'icon': 'PX',
        'color': '#06B6D4'
    }

    # Check Cohere
    cohere_status = "offline"
    cohere_key = os.getenv('COHERE_API_KEY')
    if cohere_key:
        cohere_status = "ready"
    providers['cohere'] = {
        'name': 'Cohere',
        'status': cohere_status,
        'icon': 'CO',
        'color': '#EF4444'
    }

    # Check HuggingFace
    hf_status = "offline"
    hf_key = os.getenv('HUGGINGFACE_API_KEY') or os.getenv('HF_API_KEY')
    if hf_key:
        hf_status = "ready"
    providers['huggingface'] = {
        'name': 'HuggingFace',
        'status': hf_status,
        'icon': 'HF',
        'color': '#FBBF24'
    }

    # Check Cloudflare Workers AI
    cf_status = "offline"
    cf_key = os.getenv('CLOUDFLARE_API_KEY') or os.getenv('CF_API_TOKEN')
    cf_account = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    if cf_key and cf_account:
        cf_status = "ready"
    providers['cloudflare'] = {
        'name': 'Cloudflare',
        'status': cf_status,
        'icon': 'CF',
        'color': '#F48120'
    }

    # Check Ollama (Local)
    ollama_status = "offline"
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:11434/api/tags",
                timeout=aiohttp.ClientTimeout(total=2)
            ) as resp:
                if resp.status == 200:
                    ollama_status = "ready"
    except:
        pass
    providers['ollama'] = {
        'name': 'Ollama',
        'status': ollama_status,
        'icon': 'OL',
        'color': '#A855F7'
    }

    # Count ready providers
    ready_count = sum(1 for p in providers.values() if p['status'] == 'ready')

    return {
        "providers": providers,
        "ready_count": ready_count,
        "total_count": len(providers),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/stats")
async def get_statistics():
    """Get system statistics"""
    try:
        stats = db.get_statistics()
        # Add last_updated timestamp
        stats['last_updated'] = datetime.utcnow().isoformat()
        return stats
    except Exception as e:
        import traceback
        logger.error(f"Error in /stats endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# USER PROFILE ENDPOINTS
# ============================================================================

@app.get("/profile", response_model=APIResponse)
async def get_profile():
    """Get user profile settings"""
    try:
        profile = db.get_user_profile()
        return APIResponse(
            success=True,
            message="Profile retrieved",
            data=profile
        )
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/profile", response_model=APIResponse)
async def update_profile(profile_data: dict):
    """Update user profile settings"""
    try:
        # Get current profile and merge updates
        current = db.get_user_profile()

        # Validate and update allowed fields
        allowed_fields = [
            'display_name', 'store_name', 'collector_type',
            'favorite_publishers', 'voice_preference', 'greeting_style'
        ]

        for field in allowed_fields:
            if field in profile_data:
                current[field] = profile_data[field]

        db.save_user_profile(current)

        return APIResponse(
            success=True,
            message="Profile updated",
            data=current
        )
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/settings", response_model=APIResponse)
async def get_settings():
    """Get all system settings"""
    try:
        configs = db.get_all_configs()
        return APIResponse(
            success=True,
            message="Settings retrieved",
            data=configs
        )
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/settings/{key}", response_model=APIResponse)
async def update_setting(key: str, value: dict):
    """Update a specific setting"""
    try:
        import json
        db.set_config(key, json.dumps(value.get('value', '')))
        return APIResponse(
            success=True,
            message=f"Setting '{key}' updated"
        )
    except Exception as e:
        logger.error(f"Error updating setting {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMIC CRUD ENDPOINTS
# ============================================================================

@app.post("/comics", response_model=APIResponse)
async def create_comic(
    comic: ComicCreate,
    request: Request,
    user: dict = Depends(require_auth),
    rate_limit: dict = Depends(check_rate_limit("create", 50, 3600))  # 50 creates per hour
):
    """
    Create a new comic entry

    Requires authentication. Input is validated and sanitized.
    """
    try:
        # Sanitize input
        comic_data = comic.model_dump()

        if comic_data.get('title'):
            comic_data['title'] = input_validator.validate_comic_title(comic_data['title'])

        # Check for SQL injection in all string fields
        for key, value in comic_data.items():
            if isinstance(value, str):
                if input_validator.check_sql_injection(value):
                    raise HTTPException(status_code=400, detail=f"Invalid characters in {key}")
                if input_validator.check_xss(value):
                    raise HTTPException(status_code=400, detail=f"Invalid characters in {key}")

        comic_id = db.create_comic(comic_data)

        # Audit log
        await audit_logger.log(
            action="create_comic",
            user_id=user.get('user_id') if user.get('type') == 'jwt' else None,
            api_key_id=user.get('key_id') if user.get('type') == 'api_key' else None,
            resource="comic",
            resource_id=str(comic_id),
            ip_address=request.client.host if request.client else None
        )

        return APIResponse(
            success=True,
            message="Comic created successfully",
            data={"id": comic_id}
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating comic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ComicCreateWithImages(BaseModel):
    """Comic creation with base64 images - for direct webcam submission"""
    title: str
    issue_number: Optional[str] = None
    year: Optional[str] = None
    publisher: Optional[str] = None
    writer: Optional[str] = None
    artist: Optional[str] = None
    consensus_grade: Optional[float] = None
    grade_confidence: Optional[float] = None
    estimated_value: Optional[float] = None
    front_image: Optional[str] = None  # base64 encoded
    back_image: Optional[str] = None   # base64 encoded
    issue_image: Optional[str] = None  # base64 encoded (interior/issue page)
    ai_grades: Optional[Dict[str, Any]] = None
    defects: Optional[List[Dict[str, Any]]] = None

    class Config:
        extra = "ignore"  # Ignore any extra fields not defined in the model


class QuickAddComic(BaseModel):
    """Quick add comic with minimal info - grading happens later"""
    title: str
    issue_number: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    variant_description: Optional[str] = None
    notes: Optional[str] = None
    collection_id: Optional[int] = None


@app.post("/comics/add", response_model=APIResponse)
async def create_comic_with_images(
    comic: ComicCreateWithImages,
    request: Request
):
    """
    Create a comic entry with base64 images - NO AUTH REQUIRED for local desktop use.
    Saves images to disk and creates database entry.
    """
    import base64
    import uuid
    from pathlib import Path

    try:
        # Create images directory if needed
        images_dir = Path(__file__).parent.parent / "images" / "captures"
        images_dir.mkdir(parents=True, exist_ok=True)

        front_image_path = None
        back_image_path = None

        # Save front image if provided
        if comic.front_image:
            # Handle data URL format (data:image/jpeg;base64,...)
            image_data = comic.front_image
            if ',' in image_data:
                image_data = image_data.split(',')[1]

            image_bytes = base64.b64decode(image_data)
            filename = f"{uuid.uuid4().hex}_front.jpg"
            front_image_path = str(images_dir / filename)
            with open(front_image_path, 'wb') as f:
                f.write(image_bytes)
            logger.info(f"Saved front image: {front_image_path}")

        # Save back image if provided
        if comic.back_image:
            image_data = comic.back_image
            if ',' in image_data:
                image_data = image_data.split(',')[1]

            image_bytes = base64.b64decode(image_data)
            filename = f"{uuid.uuid4().hex}_back.jpg"
            back_image_path = str(images_dir / filename)
            with open(back_image_path, 'wb') as f:
                f.write(image_bytes)
            logger.info(f"Saved back image: {back_image_path}")

        # Build comic data for database
        comic_data = {
            'title': comic.title or 'Unknown',
            'issue_number': comic.issue_number,
            'publication_year': int(comic.year) if comic.year and comic.year.isdigit() else None,
            'publisher': comic.publisher,
            'front_image_path': front_image_path or '',
            'back_image_path': back_image_path,
            'consensus_grade': comic.consensus_grade,
            'grade_confidence': comic.grade_confidence,
            'estimated_value': comic.estimated_value,
            'ai_grades': comic.ai_grades,
            'defects': comic.defects,
            'writer': comic.writer,
            'artist': comic.artist
        }

        # Create comic in database
        comic_id = db.create_comic(comic_data)

        logger.info(f"Created comic #{comic_id}: {comic.title}")

        return APIResponse(
            success=True,
            message="Comic added to collection successfully",
            data={"id": comic_id, "title": comic.title}
        )

    except Exception as e:
        logger.error(f"Error creating comic with images: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/comics/add-with-images", response_model=APIResponse)
async def add_comic_with_images_rapid(
    front_image: UploadFile = File(...),
    back_image: Optional[UploadFile] = File(None),
    issue_image: Optional[UploadFile] = File(None),
    comic_data: str = Form(...)
):
    """
    Rapid capture: Add comic with images + FAST OCR for title/issue/publisher.
    Images are saved to disk, AI extracts basic info in ~1-2 seconds.
    Comic is added with 'pending' status for later full grading.
    NO AUTH REQUIRED for local desktop use.
    """
    import json
    import base64
    from datetime import datetime

    try:
        # Parse comic data JSON
        data = json.loads(comic_data)
        title = data.get('title', 'Unknown')
        issue_number = data.get('issue_number')
        publisher = data.get('publisher')

        # Read front image for fast OCR (if fields not provided)
        front_content = await front_image.read()
        await front_image.seek(0)  # Reset for saving later

        # Fast OCR to populate fields if not provided by user
        if title == 'Unknown' or not issue_number or not publisher:
            try:
                from ai_providers.groq_grader import fast_ocr_extract
                image_b64 = base64.b64encode(front_content).decode('utf-8')
                ocr_result = await fast_ocr_extract(image_b64)
                logger.info(f"Fast OCR result: {ocr_result}")

                # Only override if user didn't provide values
                if title == 'Unknown' and ocr_result.get('title'):
                    title = ocr_result['title']
                if not issue_number and ocr_result.get('issue_number'):
                    issue_number = ocr_result['issue_number']
                if not publisher and ocr_result.get('publisher'):
                    publisher = ocr_result['publisher']
            except Exception as ocr_err:
                logger.warning(f"Fast OCR failed (continuing without): {ocr_err}")

        # Generate unique filename timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')

        # Save images to disk
        images_dir = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/images/captures")
        images_dir.mkdir(parents=True, exist_ok=True)

        front_path = None
        back_path = None

        # Save front image (already read for OCR)
        if front_image:
            front_filename = f"{timestamp}_front.jpg"
            front_path = images_dir / front_filename
            with open(front_path, 'wb') as f:
                f.write(front_content)
            front_path = str(front_path)
            logger.info(f"Saved front image: {front_path}")

        # Save back image
        if back_image:
            back_filename = f"{timestamp}_back.jpg"
            back_path = images_dir / back_filename
            content = await back_image.read()
            with open(back_path, 'wb') as f:
                f.write(content)
            back_path = str(back_path)
            logger.info(f"Saved back image: {back_path}")

        # Save issue image (stored as additional metadata)
        issue_path = None
        if issue_image:
            issue_filename = f"{timestamp}_issue.jpg"
            issue_path = images_dir / issue_filename
            content = await issue_image.read()
            with open(issue_path, 'wb') as f:
                f.write(content)
            issue_path = str(issue_path)
            logger.info(f"Saved issue image: {issue_path}")

        # Create comic in database with pending status
        comic_entry = {
            'title': title,
            'issue_number': issue_number,
            'publisher': publisher,
            'front_image_path': front_path,
            'back_image_path': back_path,
            'notes': f"Issue closeup: {issue_path}" if issue_path else None
        }

        comic_id = db.create_comic(comic_entry)
        logger.info(f"Rapid capture: Created comic #{comic_id}: {title} (pending)")

        return APIResponse(
            success=True,
            message="Comic saved with images (pending grading)",
            data={
                "id": comic_id,
                "title": title,
                "grading_status": "pending",
                "front_image": front_path,
                "back_image": back_path
            }
        )

    except Exception as e:
        logger.error(f"Error in rapid capture: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/comics/fast-ocr", response_model=APIResponse)
async def fast_ocr_comic(image: UploadFile = File(...)):
    """
    Fast OCR endpoint - extracts title, issue #, publisher from cover image.
    Returns in ~1-2 seconds for quick form population.
    """
    import base64

    try:
        content = await image.read()
        image_b64 = base64.b64encode(content).decode('utf-8')

        from ai_providers.groq_grader import fast_ocr_extract
        ocr_result = await fast_ocr_extract(image_b64)
        logger.info(f"Fast OCR result: {ocr_result}")

        return APIResponse(
            success=True,
            message="OCR completed",
            data={
                "title": ocr_result.get('title', 'Unknown'),
                "issue_number": ocr_result.get('issue_number'),
                "publisher": ocr_result.get('publisher'),
                "provider": ocr_result.get('provider', 'Groq-Fast')
            }
        )
    except Exception as e:
        logger.error(f"Fast OCR error: {e}")
        return APIResponse(
            success=False,
            message=str(e),
            data={"title": "Unknown", "issue_number": None, "publisher": None}
        )


@app.post("/comics/quick-add", response_model=APIResponse)
async def quick_add_comic(comic: QuickAddComic):
    """
    Quick add a comic with minimal info - NO GRADING.
    Comic is added with 'pending' status for later grading.
    NO AUTH REQUIRED for local desktop use.
    """
    try:
        comic_data = {
            'title': comic.title,
            'issue_number': comic.issue_number,
            'publisher': comic.publisher,
            'publication_year': comic.publication_year,
            'variant_description': comic.variant_description,
            'notes': comic.notes,
            'collection_id': comic.collection_id
        }

        comic_id = db.create_comic(comic_data)
        logger.info(f"Quick added comic #{comic_id}: {comic.title} (status: pending)")

        return APIResponse(
            success=True,
            message="Comic added to collection (pending grading)",
            data={
                "id": comic_id,
                "title": comic.title,
                "grading_status": "pending"
            }
        )
    except Exception as e:
        logger.error(f"Error quick-adding comic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/comics/pending", response_model=APIResponse)
async def get_pending_comics(
    limit: int = Query(50, ge=1, le=500)
):
    """
    Get all comics with pending grading status.
    NO AUTH REQUIRED for local desktop use.
    """
    try:
        results, total = db.search_comics({
            'grading_status': 'pending',
            'limit': limit,
            'sort_by': 'date_added',
            'sort_order': 'DESC'
        })
        return APIResponse(
            success=True,
            message=f"Found {total} pending comics",
            data={
                "comics": results,
                "total": total
            }
        )
    except Exception as e:
        logger.error(f"Error getting pending comics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/comics/grade-pending", response_model=APIResponse)
async def grade_pending_comics(
    background_tasks: BackgroundTasks,
    limit: int = Query(50, ge=1, le=100)
):
    """
    Start batch grading of all pending comics.
    Runs in background and broadcasts progress via WebSocket.
    NO AUTH REQUIRED for local desktop use.
    """
    try:
        # Get pending comics
        results, total = db.search_comics({
            'grading_status': 'pending',
            'limit': limit,
            'sort_by': 'date_added',
            'sort_order': 'ASC'
        })

        if not results:
            return APIResponse(
                success=True,
                message="No pending comics to grade",
                data={"total": 0, "started": 0}
            )

        comic_ids = [c['id'] for c in results]

        # Start background grading
        background_tasks.add_task(_grade_pending_task, comic_ids)

        return APIResponse(
            success=True,
            message=f"Started grading {len(comic_ids)} comics in background",
            data={
                "total_pending": total,
                "started": len(comic_ids),
                "comic_ids": comic_ids
            }
        )
    except Exception as e:
        logger.error(f"Error starting pending grade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _grade_pending_task(comic_ids: List[int]):
    """Background task to grade pending comics"""
    from ai_consensus import consensus_grader

    for i, comic_id in enumerate(comic_ids):
        try:
            comic = db.get_comic(comic_id)
            if not comic:
                continue

            # Broadcast progress
            await ws_manager.broadcast({
                "event": "grade_pending_progress",
                "comic_id": comic_id,
                "title": comic.get('title'),
                "progress": i + 1,
                "total": len(comic_ids),
                "status": "grading"
            })

            # Check if comic has images
            front_image = comic.get('front_image_path')
            if not front_image:
                logger.warning(f"Comic {comic_id} has no front image, skipping")
                continue

            # Grade the comic
            grade_result = await consensus_grader.grade_comic(
                front_image=front_image,
                back_image=comic.get('back_image_path')
            )

            # Update database with grade
            db.update_grading(comic_id, grade_result)

            # Fetch pricing after grading
            estimated_value = 0
            consensus_grade = grade_result.get('consensus_grade', 0)
            if consensus_grade > 0:
                try:
                    from pricing_sources.ebay_scraper import fetch_ebay_price
                    ebay_result = await asyncio.wait_for(
                        fetch_ebay_price(
                            title=comic.get('title', ''),
                            issue_number=str(comic.get('issue_number', '') or ''),
                            grade=consensus_grade
                        ),
                        timeout=15
                    )
                    if ebay_result and ebay_result.get('price'):
                        estimated_value = ebay_result['price']
                        db.update_comic(comic_id, {'estimated_value': estimated_value})
                        logger.info(f"[PRICING] Comic {comic_id}: ${estimated_value}")
                except Exception as pe:
                    logger.warning(f"[PRICING] Failed for comic {comic_id}: {pe}")

            # Broadcast completion
            await ws_manager.broadcast({
                "event": "grade_pending_complete",
                "comic_id": comic_id,
                "title": comic.get('title'),
                "grade": grade_result.get('consensus_grade'),
                "estimated_value": estimated_value,
                "progress": i + 1,
                "total": len(comic_ids)
            })

        except Exception as e:
            logger.error(f"Error grading comic {comic_id}: {e}")
            await ws_manager.broadcast({
                "event": "grade_pending_error",
                "comic_id": comic_id,
                "error": str(e),
                "progress": i + 1,
                "total": len(comic_ids)
            })

    # Broadcast batch complete
    await ws_manager.broadcast({
        "event": "grade_pending_batch_complete",
        "total": len(comic_ids)
    })


@app.get("/comics/{comic_id}", response_model=APIResponse)
async def get_comic(
    comic_id: int,
    user: dict = Depends(require_auth)
):
    """Get comic by ID - requires authentication"""
    comic = db.get_comic(comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    return APIResponse(success=True, data=comic)


@app.put("/comics/{comic_id}", response_model=APIResponse)
async def update_comic(
    comic_id: int,
    data: Dict[str, Any],
    request: Request,
    rate_limit: dict = Depends(check_rate_limit("update", 100, 3600))
):
    """Update comic entry - NO AUTH for local desktop use"""
    if not db.get_comic(comic_id):
        raise HTTPException(status_code=404, detail="Comic not found")

    # Validate input data
    for key, value in data.items():
        if isinstance(value, str):
            if input_validator.check_sql_injection(value):
                raise HTTPException(status_code=400, detail=f"Invalid characters in {key}")
            if input_validator.check_xss(value):
                raise HTTPException(status_code=400, detail=f"Invalid characters in {key}")

    db.update_comic(comic_id, data)

    # Audit log
    await audit_logger.log(
        action="update_comic",
        user_id=None,
        api_key_id=None,
        resource="comic",
        resource_id=str(comic_id),
        ip_address=request.client.host if request.client else None
    )

    return APIResponse(success=True, message="Comic updated successfully")


@app.delete("/comics/{comic_id}", response_model=APIResponse)
async def delete_comic(
    comic_id: int,
    request: Request,
    user: dict = Depends(require_admin)
):
    """Delete comic - requires admin role"""
    if not db.delete_comic(comic_id):
        raise HTTPException(status_code=404, detail="Comic not found")

    # Audit log
    await audit_logger.log(
        action="delete_comic",
        user_id=user.get('user_id') if user.get('type') == 'jwt' else None,
        api_key_id=user.get('key_id') if user.get('type') == 'api_key' else None,
        resource="comic",
        resource_id=str(comic_id),
        ip_address=request.client.host if request.client else None
    )

    return APIResponse(success=True, message="Comic deleted successfully")


@app.post("/comics/search", response_model=APIResponse)
async def search_comics(
    query: ComicSearchQuery
):
    """Search comics with filters - NO AUTH for local desktop use"""
    # Validate search terms
    query_data = query.model_dump()
    for key, value in query_data.items():
        if isinstance(value, str) and value:
            if input_validator.check_sql_injection(value):
                raise HTTPException(status_code=400, detail=f"Invalid characters in {key}")

    results, total = db.search_comics(query_data)
    return APIResponse(
        success=True,
        data={
            "comics": results,
            "total": total,
            "limit": query.limit,
            "offset": query.offset
        }
    )


@app.get("/comics", response_model=APIResponse)
async def list_comics(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("date_added"),
    sort_order: str = Query("desc")
):
    """List all comics with pagination - NO AUTH for local desktop use"""
    # Validate sort parameters
    allowed_sort_fields = ['date_added', 'title', 'publisher', 'consensus_grade', 'created_at']
    if sort_by not in allowed_sort_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by. Allowed: {allowed_sort_fields}")
    if sort_order not in ['asc', 'desc']:
        raise HTTPException(status_code=400, detail="sort_order must be 'asc' or 'desc'")

    query = ComicSearchQuery(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order
    )
    results, total = db.search_comics(query.model_dump())
    return APIResponse(
        success=True,
        data={
            "comics": results,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    )


# ============================================================================
# IMAGE UPLOAD ENDPOINTS
# ============================================================================

@app.post("/upload/front/{comic_id}")
async def upload_front_image(
    comic_id: int,
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(require_auth),
    rate_limit: dict = Depends(check_rate_limit("upload", 50, 3600))  # 50 uploads per hour
):
    """Upload front cover image - requires authentication"""
    return await _upload_image(comic_id, file, "front", request, user)


@app.post("/upload/back/{comic_id}")
async def upload_back_image(
    comic_id: int,
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(require_auth),
    rate_limit: dict = Depends(check_rate_limit("upload", 50, 3600))
):
    """Upload back cover image - requires authentication"""
    return await _upload_image(comic_id, file, "back", request, user)


async def _upload_image(
    comic_id: int,
    file: UploadFile,
    side: str,
    request: Request,
    user: dict
) -> APIResponse:
    """Handle image upload and processing with validation"""
    comic = db.get_comic(comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")

    # Read file content
    content = await file.read()

    # Comprehensive file validation
    try:
        validation_result = await input_validator.validate_image_upload(
            file_content=content,
            content_type=file.content_type or "application/octet-stream"
        )
        logger.info(f"Image validated: {validation_result['width']}x{validation_result['height']}, {validation_result['size_mb']:.2f}MB")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check for path traversal in filename
    if file.filename and input_validator.check_path_traversal(file.filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Generate safe filename using UUID
    import uuid
    safe_filename = f"{comic_id}_{side}_{uuid.uuid4().hex[:8]}.jpg"
    upload_path = Path(f"P:/SOVEREIGN_APPS/collectibles_grading_system/images/captures/{safe_filename}")

    # Save file
    upload_path.write_bytes(content)

    # Audit log
    await audit_logger.log(
        action="upload_image",
        user_id=user.get('user_id') if user.get('type') == 'jwt' else None,
        api_key_id=user.get('key_id') if user.get('type') == 'api_key' else None,
        resource="comic",
        resource_id=str(comic_id),
        ip_address=request.client.host if request.client else None,
        details={
            "side": side,
            "size_mb": validation_result['size_mb'],
            "dimensions": f"{validation_result['width']}x{validation_result['height']}"
        }
    )

    # Process image
    result = image_processor.process_image(str(upload_path))

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['errors'][0] if result['errors'] else "Processing failed")

    # Update database
    update_data = {
        f"{side}_image_path": result['processed_path'],
        f"{side}_quality_score": result['quality_score'],
        f"{side}_capture_metadata": result['metadata']
    }
    db.update_comic(comic_id, update_data)

    return APIResponse(
        success=True,
        message=f"{side.title()} image uploaded and processed",
        data={
            "path": result['processed_path'],
            "quality_score": result['quality_score'],
            "preprocessing": result['preprocessing_applied']
        }
    )


# ============================================================================
# GRADING ENDPOINTS
# ============================================================================

@app.post("/grade-image")
async def grade_direct_upload(
    front_image: UploadFile = File(...),
    back_image: Optional[UploadFile] = File(None)
):
    """
    Direct grading endpoint - accepts image uploads and returns AI grading results
    Uses Claude and Gemini vision models for fast, accurate AI grading
    NO AUTHENTICATION REQUIRED for local use
    """
    import base64
    import tempfile
    import os

    try:
        # Read front image
        front_data = await front_image.read()
        front_base64 = base64.b64encode(front_data).decode('utf-8')

        # Read back image if provided
        back_base64 = None
        if back_image:
            back_data = await back_image.read()
            back_base64 = base64.b64encode(back_data).decode('utf-8')

        # Import AI providers - Claude, Gemini, Groq, Grok, and OpenRouter free models
        from ai_providers import grade_with_claude, grade_with_gemini, grade_with_groq, grade_with_grok
        from ai_providers.openrouter_grader import grade_with_openrouter, FREE_VISION_MODELS

        # Run grading with multiple AI models in parallel
        import asyncio

        # Use Claude, Gemini, and 3 OpenRouter free models for better consensus
        grading_tasks = []
        ai_grades = {}

        # Claude grading (primary - most accurate)
        claude_task = asyncio.create_task(grade_with_claude(front_base64))
        grading_tasks.append(('claude', claude_task))

        # Gemini grading (secondary - fast)
        gemini_task = asyncio.create_task(grade_with_gemini(front_base64))
        grading_tasks.append(('gemini', gemini_task))

        # Groq grading (LLaMA 3.2 Vision - very fast)
        groq_task = asyncio.create_task(grade_with_groq(front_base64))
        grading_tasks.append(('groq', groq_task))

        # xAI Grok grading (Grok vision model)
        grok_task = asyncio.create_task(grade_with_grok(front_base64))
        grading_tasks.append(('grok', grok_task))

        # DeepSeek removed - deepseek-chat is NOT a vision model (doesn't support images)

        # OpenRouter free models (use first 3 for variety)
        openrouter_models = FREE_VISION_MODELS[:3]
        for model in openrouter_models:
            model_name = model.split('/')[-1].split(':')[0]  # Extract short name
            task = asyncio.create_task(grade_with_openrouter(front_base64, model=model))
            grading_tasks.append((f'openrouter_{model_name}', task))

        # Wait for all tasks - 60 second timeout for Claude and Gemini
        results = {}
        for name, task in grading_tasks:
            try:
                result = await asyncio.wait_for(task, timeout=60)  # 60s timeout
                results[name] = result
                logger.info(f"[GRADING] {name} returned: grade={result.get('grade')}, error={result.get('error')}")
                logger.info(f"[GRADING] {name} comic_info: {result.get('comic_info', {})}")

                # Add to ai_grades if we got a valid grade (even with errors for display)
                if result.get('grade', 0) > 0:
                    ai_grades[name] = {
                        'grade': result.get('grade', 0),
                        'confidence': result.get('confidence', 0.7),
                        'model_name': result.get('model', name),
                        'provider': result.get('provider', 'Unknown'),
                        'icon': result.get('icon', '🤖'),
                        'reasoning': result.get('reasoning', ''),
                        'defects_found': result.get('defects', [])
                    }
                elif result.get('error'):
                    # Still show provider with error status so user knows what happened
                    logger.warning(f"[GRADING] {name} error: {result.get('error')}")
            except asyncio.TimeoutError:
                logger.warning(f"[GRADING] {name} timed out after 60s")
            except Exception as e:
                logger.warning(f"[GRADING] {name} failed: {e}")

        # Get comic identification from AI results (Claude, Gemini, and OpenRouter extract this)
        comic_info = {'title': 'Unidentified Comic', 'issue_number': '??', 'publisher': 'Unknown', 'year': 'Unknown'}

        # Helper function to validate issue number
        def is_valid_issue_number(issue_num):
            """Check if issue_number looks like a real issue number (numeric or simple format)"""
            if not issue_num:
                return False
            issue_str = str(issue_num).strip()
            # Invalid values
            invalid_values = ['', '??', 'Unknown', 'unknown', 'N/A', 'n/a', 'None', 'null',
                             '<issue # only, e.g. 129>', '<issue # only>', 'if visible', '<if visible>']
            if issue_str in invalid_values:
                return False
            # Should contain at least one digit
            if not re.search(r'\d', issue_str):
                return False
            # Should not be a year (4 digits starting with 19 or 20)
            if re.match(r'^(19|20)\d{2}$', issue_str):
                return False
            # Should not be a price (starts with $ or contains cents)
            if issue_str.startswith('$') or re.match(r'^\d+[¢c]$', issue_str):
                return False
            return True

        # Helper function to validate title
        def is_valid_title(title):
            if not title:
                return False
            title_str = str(title).strip()
            invalid_titles = ['', 'Unknown', 'unknown', 'Unidentified Comic', 'None', 'null',
                             'if visible', '<if visible>', '<series name>']
            return title_str not in invalid_titles

        # VOTING SYSTEM: Collect votes for issue_number and title from all AI providers
        # This prevents a single AI from providing a wrong issue number
        issue_number_votes = {}  # {normalized_issue: [providers...]}
        title_votes = {}         # {normalized_title: [providers...]}
        best_comic_info = None

        # Build list of provider names to check (including openrouter variants)
        provider_names = ['claude', 'gemini', 'groq', 'grok']
        # Add any openrouter results (they have names like openrouter_qwen2.5-vl-72b-instruct)
        for name in results.keys():
            if name.startswith('openrouter_'):
                provider_names.append(name)

        for name in provider_names:
            if name in results and isinstance(results[name], dict):
                ai_comic_info = results[name].get('comic_info', {})
                if ai_comic_info:
                    # Collect issue_number votes
                    issue_val = ai_comic_info.get('issue_number')
                    if is_valid_issue_number(issue_val):
                        # Normalize issue number
                        normalized_issue = str(issue_val).strip().lstrip('0') or '0'
                        if normalized_issue not in issue_number_votes:
                            issue_number_votes[normalized_issue] = []
                        issue_number_votes[normalized_issue].append(name)

                    # Collect title votes
                    title_val = ai_comic_info.get('title')
                    if is_valid_title(title_val):
                        normalized_title = str(title_val).strip()
                        if normalized_title not in title_votes:
                            title_votes[normalized_title] = []
                        title_votes[normalized_title].append(name)

                    # Use first valid comic_info as base for other fields
                    if best_comic_info is None and is_valid_title(ai_comic_info.get('title')):
                        best_comic_info = {
                            'title': ai_comic_info.get('title', 'Unknown'),
                            'issue_number': ai_comic_info.get('issue_number', '??'),
                            'publisher': ai_comic_info.get('publisher', 'Unknown'),
                            'year': ai_comic_info.get('year', 'Unknown'),
                            'volume': ai_comic_info.get('volume'),
                            'cover_date': ai_comic_info.get('cover_date'),
                            'cover_price': ai_comic_info.get('cover_price'),
                            'story_title': ai_comic_info.get('story_title'),
                            'writer': ai_comic_info.get('writer', []),
                            'cover_artist': ai_comic_info.get('cover_artist'),
                            'interior_artist': ai_comic_info.get('interior_artist'),
                            'editor': ai_comic_info.get('editor'),
                            'genre': ai_comic_info.get('genre', []),
                            'characters': ai_comic_info.get('characters', []),
                            'page_count': ai_comic_info.get('page_count'),
                            'format': ai_comic_info.get('format'),
                            'series_type': ai_comic_info.get('series_type'),
                            'era': ai_comic_info.get('era'),
                            'country': ai_comic_info.get('country'),
                            'language': ai_comic_info.get('language'),
                        }
                        logger.info(f"[GRADING] Got base comic_info from {name}")

        # Vote on issue_number - pick the one with most votes
        if issue_number_votes:
            winning_issue = max(issue_number_votes.items(), key=lambda x: len(x[1]))
            logger.info(f"[GRADING] Issue number votes: {issue_number_votes}")
            logger.info(f"[GRADING] Winning issue: #{winning_issue[0]} (votes: {len(winning_issue[1])} from {winning_issue[1]})")
            if best_comic_info:
                best_comic_info['issue_number'] = winning_issue[0]

        # Vote on title - pick the one with most votes
        if title_votes:
            winning_title = max(title_votes.items(), key=lambda x: len(x[1]))
            logger.info(f"[GRADING] Title votes: {title_votes}")
            logger.info(f"[GRADING] Winning title: '{winning_title[0]}' (votes: {len(winning_title[1])})")
            if best_comic_info:
                best_comic_info['title'] = winning_title[0]

        if best_comic_info:
            comic_info = best_comic_info
            logger.info(f"[GRADING] Final comic_info: {comic_info}")

        # Extract key_issue_info from first valid result
        key_issue_info = {'is_key_issue': False, 'key_reasons': [], 'first_appearances': [], 'notable_events': []}
        for name in provider_names:
            if name in results and isinstance(results[name], dict):
                ai_key_info = results[name].get('key_issue_info', {})
                if ai_key_info and ai_key_info.get('is_key_issue'):
                    key_issue_info = ai_key_info
                    logger.info(f"[GRADING] Got key_issue_info from {name}: {key_issue_info}")
                    break

        # Enrich comic info with writer/artist/year from online databases
        if comic_info.get('title') and comic_info.get('title') not in ['Unidentified Comic', 'Unknown', '']:
            try:
                from pricing_sources.comic_vine_lookup import enrich_comic_info
                comic_info = await asyncio.wait_for(
                    enrich_comic_info(comic_info),
                    timeout=10
                )
                logger.info(f"[GRADING] Enriched comic_info: {comic_info}")
            except asyncio.TimeoutError:
                logger.warning("[GRADING] Comic metadata enrichment timed out")
            except Exception as e:
                logger.warning(f"[GRADING] Comic metadata enrichment failed: {e}")

        # Run Perplexity and Cohere research in parallel for comprehensive metadata
        if comic_info.get('title') and comic_info.get('title') not in ['Unidentified Comic', 'Unknown', '']:
            try:
                from ai_providers.perplexity_research import research_comic_info as perplexity_research
                from ai_providers.cohere_research import research_comic_history as cohere_research

                research_tasks = [
                    asyncio.create_task(
                        asyncio.wait_for(
                            perplexity_research(
                                title=comic_info.get('title', ''),
                                issue_number=str(comic_info.get('issue_number', '')),
                                publisher=comic_info.get('publisher')
                            ),
                            timeout=30
                        )
                    ),
                    asyncio.create_task(
                        asyncio.wait_for(
                            cohere_research(
                                title=comic_info.get('title', ''),
                                issue_number=str(comic_info.get('issue_number', '')),
                                publisher=comic_info.get('publisher')
                            ),
                            timeout=30
                        )
                    )
                ]

                research_results = await asyncio.gather(*research_tasks, return_exceptions=True)
                perplexity_result = research_results[0] if not isinstance(research_results[0], Exception) else {}
                cohere_result = research_results[1] if not isinstance(research_results[1], Exception) else {}

                logger.info(f"[GRADING] Perplexity research: {list(perplexity_result.keys()) if isinstance(perplexity_result, dict) else 'error'}")
                logger.info(f"[GRADING] Cohere research: {list(cohere_result.keys()) if isinstance(cohere_result, dict) else 'error'}")

                # Merge Perplexity results (comprehensive metadata)
                if perplexity_result and not perplexity_result.get('error'):
                    # Creative team
                    if perplexity_result.get('creative_team'):
                        ct = perplexity_result['creative_team']
                        if not comic_info.get('writer') and ct.get('writer'):
                            comic_info['writer'] = ', '.join(ct['writer']) if isinstance(ct['writer'], list) else ct['writer']
                        if not comic_info.get('artist') and ct.get('penciler'):
                            comic_info['artist'] = ', '.join(ct['penciler']) if isinstance(ct['penciler'], list) else ct['penciler']
                        if ct.get('inker'):
                            comic_info['inker'] = ', '.join(ct['inker']) if isinstance(ct['inker'], list) else ct['inker']
                        if ct.get('colorist'):
                            comic_info['colorist'] = ', '.join(ct['colorist']) if isinstance(ct['colorist'], list) else ct['colorist']
                        if ct.get('letterer'):
                            comic_info['letterer'] = ', '.join(ct['letterer']) if isinstance(ct['letterer'], list) else ct['letterer']
                        if ct.get('cover_artist'):
                            comic_info['cover_artist'] = ct['cover_artist']
                        if ct.get('editor'):
                            comic_info['editor'] = ', '.join(ct['editor']) if isinstance(ct['editor'], list) else ct['editor']

                    # Story details
                    if perplexity_result.get('story'):
                        story = perplexity_result['story']
                        if story.get('title'):
                            comic_info['story_title'] = story['title']
                        if story.get('summary'):
                            comic_info['story_summary'] = story['summary']
                        if story.get('characters'):
                            comic_info['characters'] = story['characters']
                        if story.get('villains'):
                            comic_info['villains'] = story['villains']

                    # Key issue info from Perplexity
                    if perplexity_result.get('key_issue'):
                        ki = perplexity_result['key_issue']
                        if ki.get('is_key'):
                            key_issue_info['is_key_issue'] = True
                            if ki.get('reasons'):
                                key_issue_info['key_reasons'] = ki['reasons']
                            if ki.get('first_appearances'):
                                key_issue_info['first_appearances'] = ki['first_appearances']
                            if ki.get('iconic_cover'):
                                key_issue_info['notable_events'].append('Iconic Cover')

                    # Historical context
                    if perplexity_result.get('historical'):
                        hist = perplexity_result['historical']
                        if hist.get('era'):
                            comic_info['era'] = hist['era']
                        if hist.get('significance'):
                            comic_info['historical_significance'] = hist['significance']
                        if hist.get('collected_in'):
                            comic_info['collected_editions'] = hist['collected_in']

                    # Publication info
                    if perplexity_result.get('cover_date'):
                        comic_info['cover_date'] = perplexity_result['cover_date']
                    if perplexity_result.get('cover_price'):
                        comic_info['cover_price'] = perplexity_result['cover_price']
                    if perplexity_result.get('page_count'):
                        comic_info['page_count'] = perplexity_result['page_count']

                # Merge Cohere results (history and significance)
                if cohere_result and not cohere_result.get('error'):
                    # History section
                    if cohere_result.get('history'):
                        history = cohere_result['history']
                        if history.get('publication'):
                            pub = history['publication']
                            if not comic_info.get('cover_date') and pub.get('date'):
                                comic_info['cover_date'] = pub['date']
                            if not comic_info.get('era') and pub.get('era'):
                                comic_info['era'] = pub['era']
                        if history.get('story') and not comic_info.get('story_summary'):
                            if history['story'].get('summary'):
                                comic_info['story_summary'] = history['story']['summary']
                        if history.get('significance'):
                            sig = history['significance']
                            if sig.get('is_key_issue'):
                                key_issue_info['is_key_issue'] = True
                            if sig.get('key_reasons'):
                                key_issue_info['key_reasons'] = list(set(key_issue_info.get('key_reasons', []) + sig['key_reasons']))
                            if sig.get('first_appearances'):
                                key_issue_info['first_appearances'] = list(set(key_issue_info.get('first_appearances', []) + sig['first_appearances']))
                            if sig.get('notable_events'):
                                key_issue_info['notable_events'] = list(set(key_issue_info.get('notable_events', []) + sig['notable_events']))
                            if sig.get('collector_notes'):
                                comic_info['collector_notes'] = sig['collector_notes']

                    # Metadata section (creative team from Cohere if not from Perplexity)
                    if cohere_result.get('metadata', {}).get('creative_team'):
                        ct = cohere_result['metadata']['creative_team']
                        if not comic_info.get('writer') and ct.get('writer'):
                            comic_info['writer'] = ', '.join(ct['writer']) if isinstance(ct['writer'], list) else ct['writer']
                        if not comic_info.get('artist') and ct.get('penciler'):
                            comic_info['artist'] = ct['penciler']

                    # Characters from Cohere
                    if cohere_result.get('metadata', {}).get('characters'):
                        chars = cohere_result['metadata']['characters']
                        if not comic_info.get('characters') and chars.get('featured'):
                            comic_info['characters'] = chars['featured']
                        if not comic_info.get('villains') and chars.get('villains'):
                            comic_info['villains'] = chars['villains']

                logger.info(f"[GRADING] Enriched comic_info with research: writer={comic_info.get('writer')}, artist={comic_info.get('artist')}, story={comic_info.get('story_title')}")

            except asyncio.TimeoutError:
                logger.warning("[GRADING] Research providers timed out")
            except Exception as e:
                logger.warning(f"[GRADING] Research enrichment failed: {e}")

        # Calculate consensus grade
        if ai_grades:
            grades = [g['grade'] for g in ai_grades.values() if g['grade'] > 0]
            if grades:
                avg_grade = sum(grades) / len(grades)
                min_grade = min(grades)
                consensus_grade = round(((avg_grade * 0.6) + (min_grade * 0.4)) * 2) / 2
            else:
                consensus_grade = 6.0
        else:
            consensus_grade = 6.0

        # Combine all defects
        all_defects = []
        for result in results.values():
            if isinstance(result, dict):
                all_defects.extend(result.get('defects', []))

        # Calculate confidence
        if len(ai_grades) >= 2:
            grade_values = [g['grade'] for g in ai_grades.values()]
            avg = sum(grade_values) / len(grade_values)
            variance = sum((g - avg) ** 2 for g in grade_values) / len(grade_values)
            std_dev = variance ** 0.5
            confidence = max(0.5, min(0.98, 1 - (std_dev / 3)))
        else:
            confidence = 0.7

        # Fetch pricing from multiple sources
        estimated_value = 0
        ebay_data = None
        cgc_data = None
        pricing_sources_used = []

        logger.info(f"[PRICING] Looking up prices for grade {consensus_grade}")

        if comic_info.get('title') and comic_info.get('title') not in ['Unidentified Comic', 'Unknown', '']:
            # Fetch eBay and CGC pricing in parallel
            pricing_tasks = []

            # eBay sold listings
            async def fetch_ebay():
                try:
                    from pricing_sources.ebay_scraper import fetch_ebay_price
                    return await fetch_ebay_price(
                        title=comic_info.get('title', ''),
                        issue_number=comic_info.get('issue_number'),
                        grade=consensus_grade,
                        category='comics'
                    )
                except Exception as e:
                    logger.warning(f"[PRICING] eBay error: {e}")
                    return None

            # CGC census/pricing
            async def fetch_cgc():
                try:
                    from pricing_sources.cgc_lookup import fetch_cgc_data
                    return await fetch_cgc_data(
                        title=comic_info.get('title', ''),
                        issue_number=comic_info.get('issue_number'),
                        grade=consensus_grade
                    )
                except Exception as e:
                    logger.warning(f"[PRICING] CGC error: {e}")
                    return None

            # Run pricing lookups with SEPARATE timeouts so CGC data is preserved even if eBay times out
            # CGC is fast (1-2 seconds), eBay Playwright is slow (20+ seconds)
            cgc_result = None
            ebay_result = None

            # Fetch CGC first (fast, ~1 second)
            try:
                cgc_result = await asyncio.wait_for(fetch_cgc(), timeout=10)
                if cgc_result and not isinstance(cgc_result, Exception):
                    cgc_data = {
                        'price': cgc_result.get('price'),
                        'population_at_grade': cgc_result.get('population_at_grade'),
                        'total_graded': cgc_result.get('total_graded'),
                        'rarity': cgc_result.get('rarity'),
                        'rarity_score': cgc_result.get('rarity_score'),
                        'grade_matched': cgc_result.get('grade_matched'),
                        'confidence': cgc_result.get('confidence', 0.6),
                        'source': cgc_result.get('source', 'cgc')
                    }
                    if cgc_result.get('price'):
                        pricing_sources_used.append('cgc')
                        logger.info(f"[PRICING] CGC price: ${cgc_result.get('price')}")
            except asyncio.TimeoutError:
                logger.warning("[PRICING] CGC lookup timed out")
            except Exception as e:
                logger.warning(f"[PRICING] CGC error: {e}")

            # Fetch eBay (slow, 20-30 seconds with Playwright) - run in background, don't block
            try:
                ebay_result = await asyncio.wait_for(fetch_ebay(), timeout=30)
                if ebay_result and not isinstance(ebay_result, Exception) and ebay_result.get('price'):
                    ebay_data = {
                        'median_price': ebay_result.get('median_price'),
                        'average_price': ebay_result.get('average_price'),
                        'min_price': ebay_result.get('min_price'),
                        'max_price': ebay_result.get('max_price'),
                        'listings_count': ebay_result.get('listings_count', 0),
                        'recent_sales': ebay_result.get('recent_sales', [])[:3],
                        'confidence': ebay_result.get('confidence', 0.8)
                    }
                    pricing_sources_used.append('ebay')
                    logger.info(f"[PRICING] eBay price: ${ebay_result.get('price')}")
            except asyncio.TimeoutError:
                logger.warning("[PRICING] eBay lookup timed out (CGC data preserved)")
            except Exception as e:
                logger.warning(f"[PRICING] eBay error: {e}")

            # Calculate estimated value - prefer eBay actual sales, use CGC as fallback/supplement
            prices = []
            weights = []

            if ebay_data and ebay_data.get('median_price'):
                prices.append(ebay_data['median_price'])
                weights.append(ebay_data.get('confidence', 0.8))  # eBay actual sales are most reliable

            if cgc_data and cgc_data.get('price'):
                prices.append(cgc_data['price'])
                weights.append(cgc_data.get('confidence', 0.6))  # CGC estimates as fallback

            if prices:
                # Weighted average of available prices
                total_weight = sum(weights)
                if total_weight > 0:
                    estimated_value = sum(p * w for p, w in zip(prices, weights)) / total_weight
                else:
                    estimated_value = sum(prices) / len(prices)
                estimated_value = round(estimated_value, 2)
                logger.info(f"[PRICING] Final estimated value: ${estimated_value} (sources: {pricing_sources_used})")

        # Generate BREE commentary (vulgar, personality-driven feedback) - v2
        bree_commentary = None
        bree_emotion = None
        try:
            from bree_voice_feedback import get_bree, EmotionType
            bree = get_bree()
            if bree and bree.personality:
                # Check if this is a key issue
                is_key_issue = bool(comic_info.get('key_highlights'))

                # Get user profile for personalized greetings
                user_profile = db.get_user_profile()

                # Generate BREE's reaction based on grade
                response, emotion = await bree.personality.generate_response(
                    context="Reacting to comic grading result",
                    grade=consensus_grade,
                    title=comic_info.get('title', ''),
                    issue=comic_info.get('issue_number', ''),
                    value=estimated_value,
                    is_popular=is_key_issue or estimated_value > 50,
                    is_key_issue=is_key_issue,
                    defects=[d.get('type', d) if isinstance(d, dict) else str(d) for d in all_defects[:5]],
                    writer=comic_info.get('writer', ''),
                    artist=comic_info.get('artist', ''),
                    publisher=comic_info.get('publisher', ''),
                    user_profile=user_profile
                )
                bree_commentary = response
                bree_emotion = emotion.value if emotion else 'neutral'
                logger.info(f"[BREE] Generated commentary: {bree_commentary[:100]}...")
        except Exception as e:
            logger.warning(f"[BREE] Commentary generation failed: {e}")
            # Fallback to static BREE-style commentary based on grade
            if consensus_grade >= 9.5:
                bree_commentary = f"Holy shit, {consensus_grade}?! That's fucking beautiful! This is what I'm talking about!"
            elif consensus_grade >= 9.0:
                bree_commentary = f"Damn, {consensus_grade} grade! Not bad at all. Actually pretty impressive."
            elif consensus_grade >= 8.0:
                bree_commentary = f"A solid {consensus_grade}. Nothing to complain about. Could be worse."
            elif consensus_grade >= 7.0:
                bree_commentary = f"A {consensus_grade}, huh? It's alright I guess. Seen better, seen worse."
            elif consensus_grade >= 6.0:
                bree_commentary = f"Really? A {consensus_grade}? That's pretty damn mediocre if you ask me."
            elif consensus_grade >= 5.0:
                bree_commentary = f"What the hell happened to this thing? A {consensus_grade}? That's rough, buddy."
            elif consensus_grade >= 4.0:
                bree_commentary = f"A {consensus_grade}?! Did someone use this as a coaster? This is sad."
            else:
                bree_commentary = f"Are you kidding me? A {consensus_grade}?! This isn't a comic, it's garbage!"
            bree_emotion = 'nuclear' if consensus_grade < 4.0 else 'pissed' if consensus_grade < 6.0 else 'neutral' if consensus_grade < 8.0 else 'impressed'

        return {
            'comic': comic_info,
            'key_issue_info': key_issue_info,
            'consensus_grade': consensus_grade,
            'grade_label': get_grade_label(consensus_grade),
            'confidence': confidence,
            'ai_grades': ai_grades,
            'defects': all_defects[:10],  # Limit defects
            'model_count': len(ai_grades),
            'estimated_value': estimated_value,
            'ebay_data': ebay_data,
            'cgc_data': cgc_data,
            'pricing_sources': pricing_sources_used,
            'grading_notes': f'Real AI grading using {len(ai_grades)} providers: {", ".join(ai_grades.keys())}',
            'bree_commentary': bree_commentary,
            'bree_emotion': bree_emotion
        }

    except Exception as e:
        logger.error(f"Direct grading error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/identify")
async def identify_comic(image: UploadFile = File(...)):
    """
    Identify comic title, issue, publisher from cover image
    Uses Gemini AI vision to read the cover (fast)
    """
    import base64

    try:
        image_data = await image.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        from ai_providers import grade_with_gemini

        # Use Gemini for identification - it extracts comic_info as part of grading
        result = await grade_with_gemini(image_base64)
        comic_info = result.get('comic_info', {})

        if not comic_info or not comic_info.get('title'):
            comic_info = {'title': 'Unknown', 'issue_number': '??', 'publisher': 'Unknown', 'year': 'Unknown'}

        return {'comic': comic_info, 'success': True}

    except Exception as e:
        logger.error(f"Comic identification error: {e}")
        return {'comic': {'title': 'Identification Failed', 'error': str(e)}, 'success': False}


class BreeSpeakRequest(BaseModel):
    """Request for BREE to speak narration with ElevenLabs"""
    text: str
    emotion: Optional[str] = "neutral"


@app.post("/bree-speak")
async def bree_speak(request: BreeSpeakRequest):
    """
    Generate BREE's voice narration using ElevenLabs TTS.
    Returns base64-encoded MP3 audio that the frontend can play.
    """
    import base64

    try:
        from bree_voice_feedback import get_bree, EmotionType

        bree = get_bree()

        if not bree or not bree.enabled:
            logger.warning("[BREE] Voice system not enabled, returning text only")
            return {
                'success': False,
                'audio': None,
                'text': request.text,
                'emotion': request.emotion,
                'error': 'BREE voice system not enabled (ElevenLabs not configured)'
            }

        # Map emotion string to EmotionType enum
        emotion_map = {
            'ecstatic': EmotionType.ECSTATIC,
            'impressed': EmotionType.IMPRESSED,
            'pleased': EmotionType.PLEASED,
            'neutral': EmotionType.NEUTRAL,
            'annoyed': EmotionType.ANNOYED,
            'pissed': EmotionType.PISSED,
            'furious': EmotionType.FURIOUS,
            'nuclear': EmotionType.NUCLEAR
        }
        emotion = emotion_map.get(request.emotion, EmotionType.NEUTRAL)

        # Generate audio file
        audio_path = await bree._generate_audio(request.text, emotion)

        if audio_path and audio_path.exists():
            # Read and encode the audio file
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            logger.info(f"[BREE] Generated audio for: {request.text[:50]}...")

            return {
                'success': True,
                'audio': audio_base64,
                'audio_format': 'mp3',
                'text': request.text,
                'emotion': request.emotion
            }
        else:
            logger.warning("[BREE] Audio generation failed")
            return {
                'success': False,
                'audio': None,
                'text': request.text,
                'emotion': request.emotion,
                'error': 'Audio generation failed'
            }

    except Exception as e:
        logger.error(f"[BREE] Speak error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'audio': None,
            'text': request.text,
            'error': str(e)
        }


class RaistlinSpeakRequest(BaseModel):
    """Request for Raistlin to speak narration with ElevenLabs"""
    text: str
    emotion: Optional[str] = "neutral"


@app.post("/raistlin-speak")
async def raistlin_speak(request: RaistlinSpeakRequest):
    """
    Generate Raistlin's voice narration using ElevenLabs TTS.
    Returns base64-encoded MP3 audio that the frontend can play.
    Raistlin speaks slower, more deliberately like an archmage.
    """
    import base64

    try:
        from raistlin_voice_feedback import get_raistlin, EmotionType

        raistlin = get_raistlin()

        if not raistlin or not raistlin.enabled:
            logger.warning("[RAISTLIN] Voice system not enabled, returning text only")
            return {
                'success': False,
                'audio': None,
                'text': request.text,
                'emotion': request.emotion,
                'error': 'Raistlin voice system not enabled (ElevenLabs not configured)'
            }

        # Map emotion string to EmotionType enum
        emotion_map = {
            'triumphant': EmotionType.TRIUMPHANT,
            'impressed': EmotionType.IMPRESSED,
            'pleased': EmotionType.PLEASED,
            'neutral': EmotionType.NEUTRAL,
            'contemplative': EmotionType.CONTEMPLATIVE,
            'sardonic': EmotionType.SARDONIC,
            'mysterious': EmotionType.MYSTERIOUS,
            'concerned': EmotionType.CONCERNED,
            'urgent': EmotionType.URGENT
        }
        emotion = emotion_map.get(request.emotion, EmotionType.NEUTRAL)

        # Generate audio file
        audio_path = await raistlin._generate_audio(request.text, emotion)

        if audio_path and audio_path.exists():
            # Read and encode the audio file
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            logger.info(f"[RAISTLIN] Generated audio for: {request.text[:50]}...")

            return {
                'success': True,
                'audio': audio_base64,
                'audio_format': 'mp3',
                'text': request.text,
                'emotion': request.emotion
            }
        else:
            logger.warning("[RAISTLIN] Audio generation failed")
            return {
                'success': False,
                'audio': None,
                'text': request.text,
                'emotion': request.emotion,
                'error': 'Audio generation failed'
            }

    except Exception as e:
        logger.error(f"[RAISTLIN] Speak error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'audio': None,
            'text': request.text,
            'error': str(e)
        }


class CollectionMasterSpeakRequest(BaseModel):
    """Request for Collection Master (Gandalf-style) to speak"""
    text: str
    emotion: Optional[str] = "thoughtful"
    grade: Optional[float] = None
    title: Optional[str] = None
    issue_number: Optional[str] = None
    defects: Optional[List[str]] = []
    is_key_issue: Optional[bool] = False
    key_reasons: Optional[List[str]] = []


@app.post("/collection-master-speak")
async def collection_master_speak(request: CollectionMasterSpeakRequest):
    """
    Generate Collection Master's voice narration - Gandalf-like wise guardian.
    Returns base64-encoded MP3 audio. NO double-speak - frontend only calls this.
    """
    import base64

    try:
        from collection_master_voice import get_collection_master, MasterEmotion

        master = get_collection_master()

        if not master or not master.enabled:
            logger.warning("[COLLECTION_MASTER] Voice system not enabled")
            return {
                'success': False,
                'audio': None,
                'text': request.text,
                'emotion': request.emotion,
                'error': 'Collection Master voice not enabled (ElevenLabs not configured)'
            }

        # Map emotion string to MasterEmotion enum
        emotion_map = {
            'wonder': MasterEmotion.WONDER,
            'approval': MasterEmotion.APPROVAL,
            'thoughtful': MasterEmotion.THOUGHTFUL,
            'concerned': MasterEmotion.CONCERNED,
            'disappointed': MasterEmotion.DISAPPOINTED,
            'urgent': MasterEmotion.URGENT,
        }
        
        # Auto-detect emotion from grade if provided
        if request.grade is not None and request.emotion == "thoughtful":
            emotion = master.get_emotion_for_grade(request.grade)
        else:
            emotion = emotion_map.get(request.emotion, MasterEmotion.THOUGHTFUL)

        # Generate audio
        audio_path = await master.generate_audio(request.text, emotion)

        if audio_path and audio_path.exists():
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            logger.info(f"[COLLECTION_MASTER] Generated audio: {request.text[:50]}...")

            return {
                'success': True,
                'audio': audio_base64,
                'audio_format': 'mp3',
                'text': request.text,
                'emotion': emotion.value
            }
        else:
            logger.warning("[COLLECTION_MASTER] Audio generation failed")
            return {
                'success': False,
                'audio': None,
                'text': request.text,
                'emotion': request.emotion,
                'error': 'Audio generation failed'
            }

    except Exception as e:
        logger.error(f"[COLLECTION_MASTER] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'audio': None,
            'text': request.text,
            'error': str(e)
        }


@app.post("/collection-master-grading")
async def collection_master_grading_commentary(request: CollectionMasterSpeakRequest):
    """
    Generate Collection Master's dynamic grading commentary with voice.
    Uses Claude OAuth for unique responses, then ElevenLabs TTS.
    """
    import base64

    try:
        from collection_master_voice import get_collection_master

        master = get_collection_master()

        if not master:
            return {'success': False, 'error': 'Collection Master not initialized'}

        # Generate dynamic commentary
        commentary, emotion = await master.generate_grading_commentary(
            grade=request.grade or 5.0,
            title=request.title or "Unknown",
            issue=request.issue_number or "?",
            defects=request.defects or [],
            is_key_issue=request.is_key_issue or False,
            key_reasons=request.key_reasons or []
        )

        # Generate audio if enabled
        audio_base64 = None
        if master.enabled:
            audio_path = await master.generate_audio(commentary, emotion)
            if audio_path and audio_path.exists():
                with open(audio_path, 'rb') as f:
                    audio_base64 = base64.b64encode(f.read()).decode('utf-8')

        return {
            'success': True,
            'commentary': commentary,
            'emotion': emotion.value,
            'audio': audio_base64,
            'audio_format': 'mp3' if audio_base64 else None
        }

    except Exception as e:
        logger.error(f"[COLLECTION_MASTER] Grading commentary error: {e}")
        return {'success': False, 'error': str(e)}


class DynamicCommentaryRequest(BaseModel):
    """Request for dynamic AI-generated grading commentary"""
    personality: str = "bree"  # 'bree' or 'raistlin'
    grade: float
    title: str = "Unknown Comic"
    issue_number: str = ""
    publisher: str = ""
    value: float = 0
    defects: List[str] = []
    key_highlights: List[str] = []
    is_key_issue: bool = False


@app.post("/generate-commentary")
async def generate_dynamic_commentary(request: DynamicCommentaryRequest):
    """
    Generate dynamic, intelligent commentary using Claude OAuth.
    NEVER the same twice - pure AI-generated personality responses.
    """
    import base64
    import httpx

    try:
        # Get Claude OAuth token
        oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
        if not oauth_token:
            return {'success': False, 'error': 'Claude OAuth token not configured'}

        # Build personality-specific prompt
        if request.personality == 'raistlin':
            system_prompt = """You are Raistlin Majere, the powerful archmage from Dragonlance. You have hourglass eyes that see all flaws.
You speak in a slow, deliberate, mysterious manner with archaic formality and dark wit. You reference magic, the Conclave, the Tower of High Sorcery, and your brother Caramon.
Keep responses to 2-4 sentences. Be sardonic for low grades, impressed for high grades."""
            
            user_prompt = f"""Grade this comic and react in character:
- Title: {request.title} {f'#{request.issue_number}' if request.issue_number else ''}
- Publisher: {request.publisher}
- Grade: {request.grade}/10
- Value: ${request.value}
- Defects: {', '.join(request.defects) if request.defects else 'None detected'}
- Key Issue: {'Yes - ' + ', '.join(request.key_highlights) if request.key_highlights else 'No'}

React as Raistlin would - mysterious, wise, with your signature dark wit."""
        else:
            # BREE personality
            system_prompt = """You are BREE, a brutally honest, vulgar comic grader who LOVES high-grade valuable comics and DESPISES garbage.
You curse freely (shit, damn, hell, ass). You're enthusiastic for 9.0+ grades, neutral for 7-8, annoyed for 5-6, and furious for below 5.
Keep responses to 2-4 sentences. Be genuine and entertaining."""
            
            user_prompt = f"""Grade this comic and react in character:
- Title: {request.title} {f'#{request.issue_number}' if request.issue_number else ''}
- Publisher: {request.publisher}  
- Grade: {request.grade}/10
- Value: ${request.value}
- Defects: {', '.join(request.defects) if request.defects else 'None detected'}
- Key Issue: {'Yes - ' + ', '.join(request.key_highlights) if request.key_highlights else 'No'}

React as BREE would - vulgar, honest, entertaining."""

        # Call Claude API with OAuth
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": oauth_token,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 200,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}]
                }
            )

            if response.status_code == 200:
                result = response.json()
                commentary = result.get('content', [{}])[0].get('text', '')
                logger.info(f"[DYNAMIC] Generated {request.personality} commentary: {commentary[:50]}...")
                
                # Determine emotion based on grade
                if request.personality == 'raistlin':
                    if request.grade >= 9.0:
                        emotion = 'triumphant'
                    elif request.grade >= 7.0:
                        emotion = 'neutral'
                    elif request.grade >= 5.0:
                        emotion = 'contemplative'
                    else:
                        emotion = 'sardonic'
                else:
                    if request.grade >= 9.0:
                        emotion = 'ecstatic'
                    elif request.grade >= 7.0:
                        emotion = 'neutral'
                    elif request.grade >= 5.0:
                        emotion = 'annoyed'
                    else:
                        emotion = 'nuclear'

                return {
                    'success': True,
                    'commentary': commentary,
                    'emotion': emotion,
                    'personality': request.personality
                }
            else:
                logger.error(f"[DYNAMIC] Claude API error: {response.status_code} - {response.text}")
                return {'success': False, 'error': f'Claude API error: {response.status_code}'}

    except Exception as e:
        logger.error(f"[DYNAMIC] Commentary generation error: {e}")
        return {'success': False, 'error': str(e)}


class ClaudeChatRequest(BaseModel):
    """Chat request for Claude assistant"""
    message: str
    context: Optional[str] = None  # 'organize', 'analyze', 'missing', or None
    access_token: Optional[str] = None  # OAuth access token
    comic_id: Optional[int] = None  # Specific comic ID to ask about (includes images)
    include_images: Optional[bool] = False  # Whether to include comic images in request
    allow_modifications: Optional[bool] = True  # Allow Claude to modify comic entries


# Tool definitions for Claude to modify comics
CLAUDE_COMIC_TOOLS = [
    {
        "name": "update_comic",
        "description": "Update a comic book entry in the catalog. Use this when the user asks you to change, correct, or update information about a comic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "comic_id": {
                    "type": "integer",
                    "description": "The ID of the comic to update"
                },
                "title": {
                    "type": "string",
                    "description": "The comic title (e.g., 'Iron Man', 'Amazing Spider-Man')"
                },
                "issue_number": {
                    "type": "string",
                    "description": "The issue number (e.g., '1', '129', '300')"
                },
                "publisher": {
                    "type": "string",
                    "description": "The publisher name (e.g., 'Marvel Comics', 'DC Comics')"
                },
                "publication_year": {
                    "type": "integer",
                    "description": "The year the comic was published"
                },
                "key_issue": {
                    "type": "boolean",
                    "description": "Whether this is a key issue (first appearance, major event, etc.)"
                },
                "key_issue_reason": {
                    "type": "string",
                    "description": "Reason why this is a key issue (e.g., 'First appearance of Wolverine')"
                },
                "variant_description": {
                    "type": "string",
                    "description": "Description of variant cover if applicable"
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes about the comic"
                },
                "estimated_value": {
                    "type": "number",
                    "description": "Estimated value in dollars"
                }
            },
            "required": ["comic_id"]
        }
    },
    {
        "name": "get_comic_details",
        "description": "Get detailed information about a specific comic by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "comic_id": {
                    "type": "integer",
                    "description": "The ID of the comic to retrieve"
                }
            },
            "required": ["comic_id"]
        }
    },
    {
        "name": "search_comics",
        "description": "Search for comics in the catalog by title, publisher, or other criteria",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Comic title to search for"
                },
                "publisher": {
                    "type": "string",
                    "description": "Publisher to filter by"
                },
                "key_issues_only": {
                    "type": "boolean",
                    "description": "Only return key issues"
                }
            }
        }
    }
]


def execute_claude_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool called by Claude and return the result"""
    try:
        if tool_name == "update_comic":
            comic_id = tool_input.pop("comic_id")
            # Filter out None values
            update_data = {k: v for k, v in tool_input.items() if v is not None}
            if update_data:
                success = db.update_comic(comic_id, update_data)
                if success:
                    updated_comic = db.get_comic(comic_id)
                    return {
                        "success": True,
                        "message": f"Successfully updated comic ID {comic_id}",
                        "updated_fields": list(update_data.keys()),
                        "comic": updated_comic
                    }
                else:
                    return {"success": False, "error": f"Failed to update comic ID {comic_id}"}
            else:
                return {"success": False, "error": "No fields provided to update"}

        elif tool_name == "get_comic_details":
            comic = db.get_comic(tool_input["comic_id"])
            if comic:
                return {"success": True, "comic": comic}
            else:
                return {"success": False, "error": "Comic not found"}

        elif tool_name == "search_comics":
            search_params = {}
            if tool_input.get("title"):
                search_params["title"] = tool_input["title"]
            if tool_input.get("publisher"):
                search_params["publisher"] = tool_input["publisher"]
            if tool_input.get("key_issues_only"):
                search_params["key_issue"] = True
            results, total = db.search_comics(search_params)
            return {"success": True, "results": results[:20], "total": total}

        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {"success": False, "error": str(e)}


# OAuth configuration for Anthropic
ANTHROPIC_OAUTH_CONFIG = {
    "authorization_url": "https://console.anthropic.com/oauth/authorize",
    "token_url": "https://console.anthropic.com/oauth/token",
    "client_id": None,  # Set via environment variable
    "redirect_uri": "http://localhost:8000/claude/oauth/callback",
    "scope": "messages:write"
}

# Store OAuth tokens in memory (in production, use secure storage)
oauth_tokens = {}


@app.get("/claude/oauth/config")
async def get_claude_oauth_config():
    """Get OAuth configuration for Claude"""
    import os
    client_id = os.getenv('ANTHROPIC_OAUTH_CLIENT_ID')

    if not client_id:
        return {
            'success': False,
            'oauth_available': False,
            'message': 'OAuth not configured. Set ANTHROPIC_OAUTH_CLIENT_ID in .env'
        }

    return {
        'success': True,
        'oauth_available': True,
        'authorization_url': ANTHROPIC_OAUTH_CONFIG['authorization_url'],
        'client_id': client_id,
        'redirect_uri': ANTHROPIC_OAUTH_CONFIG['redirect_uri'],
        'scope': ANTHROPIC_OAUTH_CONFIG['scope']
    }


@app.get("/claude/oauth/callback")
async def claude_oauth_callback(code: str = None, error: str = None):
    """Handle OAuth callback from Anthropic"""
    import os
    import aiohttp

    if error:
        return JSONResponse(content={
            'success': False,
            'error': error
        }, status_code=400)

    if not code:
        return JSONResponse(content={
            'success': False,
            'error': 'No authorization code received'
        }, status_code=400)

    client_id = os.getenv('ANTHROPIC_OAUTH_CLIENT_ID')
    client_secret = os.getenv('ANTHROPIC_OAUTH_CLIENT_SECRET')

    if not client_id or not client_secret:
        return JSONResponse(content={
            'success': False,
            'error': 'OAuth credentials not configured'
        }, status_code=500)

    # Exchange code for token
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ANTHROPIC_OAUTH_CONFIG['token_url'],
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': ANTHROPIC_OAUTH_CONFIG['redirect_uri'],
                    'client_id': client_id,
                    'client_secret': client_secret
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return JSONResponse(content={
                        'success': False,
                        'error': f'Token exchange failed: {error_text}'
                    }, status_code=400)

                token_data = await response.json()
                # Store token (in production, associate with user session)
                oauth_tokens['default'] = token_data

                # Return HTML that closes the popup and notifies parent
                return HTMLResponse(content="""
                    <html>
                    <body>
                        <h2>Authentication Successful!</h2>
                        <p>You can close this window.</p>
                        <script>
                            if (window.opener) {
                                window.opener.postMessage({type: 'claude_oauth_success'}, '*');
                                window.close();
                            }
                        </script>
                    </body>
                    </html>
                """)

    except Exception as e:
        return JSONResponse(content={
            'success': False,
            'error': str(e)
        }, status_code=500)


@app.get("/claude/oauth/status")
async def claude_oauth_status():
    """Check if user is authenticated with Claude"""
    import os

    # Check if we have a stored token
    if 'default' in oauth_tokens:
        return {
            'authenticated': True,
            'method': 'oauth'
        }

    # Check if API key is available as fallback
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        return {
            'authenticated': True,
            'method': 'api_key'
        }

    return {
        'authenticated': False,
        'oauth_available': bool(os.getenv('ANTHROPIC_OAUTH_CLIENT_ID'))
    }


def get_claude_oauth_token() -> Optional[str]:
    """
    Load Claude OAuth token from multiple sources (priority order):
    1. Environment variable CLAUDE_CODE_OAUTH_TOKEN
    2. Config file P:/SOVEREIGN_APPS/collectibles_grading_system/config/Claude_code_oauths.txt
    3. Credentials file ~/.claude/.credentials.json
    """
    # Priority 1: Environment variable
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if token and token.startswith("sk-ant-oat01-"):
        logger.info("OAuth token loaded from environment variable")
        return token

    # Priority 2: Config file (most reliable, manually maintained)
    config_path = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/config/Claude_code_oauths.txt")
    if config_path.exists():
        try:
            content = config_path.read_text()
            # Extract token from file (format: "sk-ant-oat01-..." on line 3)
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith("sk-ant-oat01-"):
                    logger.info("OAuth token loaded from config file")
                    return line
        except Exception as e:
            logger.warning(f"Failed to read OAuth token from config file: {e}")

    # Priority 3: Credentials file
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if creds_path.exists():
        try:
            creds = json.loads(creds_path.read_text())
            oauth_data = creds.get("claudeAiOauth", {})
            token = oauth_data.get("accessToken")
            if token and token.startswith("sk-ant-oat01-"):
                # Check if expired
                expires_at = oauth_data.get("expiresAt", 0)
                if expires_at > (time.time() * 1000):  # Not expired
                    logger.info("OAuth token loaded from credentials file")
                    return token
                else:
                    logger.warning("OAuth token in credentials file has expired")
        except Exception as e:
            logger.warning(f"Failed to read credentials file: {e}")

    return None


@app.post("/claude/chat")
async def claude_chat(request: ClaudeChatRequest):
    """
    Chat with Claude about your comic collection.
    Uses OAuth token directly with Anthropic SDK for $0 subscription cost.
    Fallback: OpenRouter API with free models.
    Supports vision: pass comic_id to include images for identification.
    """
    try:
        # Get collection data for context
        comics_result = db.search_comics({})  # Get all comics
        all_comics = comics_result[0] if comics_result else []
        stats = db.get_statistics()

        # Load specific comic with images if comic_id provided
        selected_comic = None
        comic_images = []  # List of base64 encoded images
        if request.comic_id:
            selected_comic = db.get_comic(request.comic_id)
            if selected_comic and request.include_images:
                # Load front and back images
                front_path = selected_comic.get('front_image_path')
                back_path = selected_comic.get('back_image_path')

                for img_path, label in [(front_path, 'front'), (back_path, 'back')]:
                    if img_path and os.path.exists(img_path):
                        try:
                            with open(img_path, 'rb') as f:
                                img_data = f.read()
                            # Determine media type
                            ext = os.path.splitext(img_path)[1].lower()
                            media_type = {
                                '.jpg': 'image/jpeg',
                                '.jpeg': 'image/jpeg',
                                '.png': 'image/png',
                                '.webp': 'image/webp',
                                '.gif': 'image/gif'
                            }.get(ext, 'image/jpeg')

                            comic_images.append({
                                'label': label,
                                'data': base64.b64encode(img_data).decode('utf-8'),
                                'media_type': media_type
                            })
                            logger.info(f"Loaded {label} image for comic {request.comic_id}: {img_path}")
                        except Exception as e:
                            logger.warning(f"Failed to load {label} image: {e}")

        # Build comprehensive context about the collection with full details
        collection_context = f"""
You are a helpful comic book collection assistant. The user has a collection with:
- Total comics: {stats.get('total_comics', 0)}
- Total value: ${stats.get('total_value', 0):,.2f}
- Average grade: {stats.get('average_grade', 0):.1f}
- Publishers: {', '.join(stats.get('publishers', [])[:10])}

COMPLETE COLLECTION INVENTORY:
"""
        for comic in all_comics[:50]:  # Include more comics for better context
            title = comic.get('title', 'Unknown')
            issue = comic.get('issue_number', '?')
            publisher = comic.get('publisher', 'Unknown Publisher')
            year = comic.get('publication_year', 'Unknown Year')
            grade = comic.get('consensus_grade', 'N/A')
            grade_label = comic.get('grade_label', '')
            value = comic.get('estimated_value', 0) or comic.get('consensus_price', 0) or 0
            key_issue = comic.get('key_issue', False)
            key_reason = comic.get('key_issue_reason', '')
            variant = comic.get('variant_description', '')
            defects = comic.get('confirmed_defects', '')

            # Build detailed comic entry
            entry = f"- {title} #{issue}"
            entry += f" | Publisher: {publisher}"
            entry += f" | Year: {year}"
            if grade and grade != 'N/A':
                entry += f" | Grade: {grade}"
                if grade_label:
                    entry += f" ({grade_label})"
            if value:
                entry += f" | Value: ${value:,.2f}"
            if key_issue:
                entry += f" | KEY ISSUE: {key_reason}"
            if variant:
                entry += f" | Variant: {variant}"
            if defects:
                try:
                    defect_list = json.loads(defects) if isinstance(defects, str) else defects
                    if defect_list:
                        entry += f" | Defects: {', '.join(defect_list[:3])}"
                except:
                    pass

            collection_context += entry + "\n"

        # Add selected comic details if specific comic is being discussed
        if selected_comic:
            collection_context += f"""
CURRENTLY SELECTED COMIC (with images attached if include_images=True):
- ID: {selected_comic.get('id')}
- Title: {selected_comic.get('title', 'Unknown')}
- Issue: #{selected_comic.get('issue_number', '?')}
- Publisher: {selected_comic.get('publisher', 'Unknown Publisher')}
- Year: {selected_comic.get('publication_year', 'Unknown Year')}
- Current Grade: {selected_comic.get('consensus_grade', 'Not graded')}
- Grade Label: {selected_comic.get('grade_label', '')}
- Estimated Value: ${selected_comic.get('estimated_value', 0) or 0:,.2f}
- Key Issue: {'YES - ' + selected_comic.get('key_issue_reason', '') if selected_comic.get('key_issue') else 'No'}
- Variant: {selected_comic.get('variant_description', 'Standard cover')}
- Confirmed Defects: {selected_comic.get('confirmed_defects', 'None noted')}
- Notes: {selected_comic.get('notes', '')}

If images are provided, analyze them to identify:
1. The exact title, issue number, publisher, and publication year from the cover
2. Visible condition issues (creases, tears, stains, spine stress, color break)
3. Whether this is a variant cover or key issue
4. Any identifying marks like price box, newsstand/direct edition
"""

        # Prepare system prompt based on context type
        tools_instruction = ""
        if request.allow_modifications:
            tools_instruction = """

You have tools available to modify the comic catalog:
- update_comic: Use this to update comic entries when the user asks you to change title, publisher, year, key issue status, notes, etc.
- get_comic_details: Use this to get full details about a specific comic
- search_comics: Use this to search the catalog

When the user asks you to update, change, correct, or fix information about a comic, USE THE update_comic TOOL to make the change. Don't just tell them what should be changed - actually make the change using the tool.

After making changes, confirm what was updated."""

        if request.context == 'organize':
            system_prompt = """You are a comic collection organization expert.
Help the user organize their collection by suggesting categories, runs to complete,
and efficient storage/display strategies. Be specific and actionable.""" + tools_instruction
        elif request.context == 'analyze':
            system_prompt = """You are a comic market analyst and value expert.
Analyze the user's collection value, identify undervalued gems, suggest comics
that might appreciate, and provide market insights.""" + tools_instruction
        elif request.context == 'missing':
            system_prompt = """You are a comic run completion specialist.
Look at the user's collection and identify missing issues in runs,
key issues they should acquire, and affordable ways to complete sets.""" + tools_instruction
        else:
            system_prompt = """You are a friendly, knowledgeable comic book assistant.
Help the user with questions about their collection, grading, pricing,
and general comic book knowledge. Be concise but thorough.""" + tools_instruction

        # ========== METHOD 1: Direct SDK with OAuth Token ==========
        # This uses the $200/month subscription for $0 additional cost
        oauth_token = get_claude_oauth_token()
        if oauth_token:
            try:
                import anthropic

                # Use OAuth token as API key - this works with subscription billing
                client = anthropic.Anthropic(api_key=oauth_token)

                logger.info("Calling Claude API with OAuth token ($0 subscription mode)")

                # Build message content - text + images if available
                message_content = []

                # Add images first (front cover, then back cover)
                if comic_images:
                    for img in comic_images:
                        message_content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": img['media_type'],
                                "data": img['data']
                            }
                        })
                        logger.info(f"Added {img['label']} cover image to message")

                # Add text message
                message_content.append({
                    "type": "text",
                    "text": request.message
                })

                # Build API call parameters
                api_params = {
                    "model": "claude-sonnet-4-20250514",  # Latest model with vision
                    "max_tokens": 2000,
                    "system": system_prompt + "\n\n" + collection_context,
                    "messages": [
                        {"role": "user", "content": message_content}
                    ]
                }

                # Add tools if modifications are allowed
                if request.allow_modifications:
                    api_params["tools"] = CLAUDE_COMIC_TOOLS

                response = client.messages.create(**api_params)

                # Handle tool use loop - Claude may call tools
                tool_results = []
                messages = [{"role": "user", "content": message_content}]
                max_tool_iterations = 5  # Prevent infinite loops

                while response.stop_reason == "tool_use" and max_tool_iterations > 0:
                    max_tool_iterations -= 1
                    logger.info(f"Claude wants to use tools, iterations remaining: {max_tool_iterations}")

                    # Build assistant message with tool calls
                    assistant_content = []
                    tool_use_blocks = []

                    for block in response.content:
                        if block.type == "text":
                            assistant_content.append({"type": "text", "text": block.text})
                        elif block.type == "tool_use":
                            assistant_content.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input
                            })
                            tool_use_blocks.append(block)

                    messages.append({"role": "assistant", "content": assistant_content})

                    # Execute each tool and collect results
                    tool_result_content = []
                    for tool_block in tool_use_blocks:
                        logger.info(f"Executing tool: {tool_block.name} with input: {tool_block.input}")
                        result = execute_claude_tool(tool_block.name, tool_block.input.copy())
                        tool_results.append({
                            "tool": tool_block.name,
                            "input": tool_block.input,
                            "result": result
                        })
                        tool_result_content.append({
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": json.dumps(result)
                        })

                    messages.append({"role": "user", "content": tool_result_content})

                    # Call Claude again with tool results
                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=2000,
                        system=system_prompt + "\n\n" + collection_context,
                        messages=messages,
                        tools=CLAUDE_COMIC_TOOLS if request.allow_modifications else None
                    )

                # Extract final text response
                response_text = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        response_text += block.text

                logger.info(f"Claude OAuth response received, length: {len(response_text)}, tool calls: {len(tool_results)}")

                return {
                    'success': True,
                    'response': response_text,
                    'tool_results': tool_results if tool_results else None,
                    'usage': {
                        'method': 'oauth_sdk',
                        'cost': '$0 (subscription)',
                        'model': 'claude-sonnet-4-20250514'
                    }
                }

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"OAuth SDK call failed: {error_msg}")

                # Check if it's an auth error - fall through to OpenRouter
                if 'authentication' in error_msg.lower() or '401' in error_msg or 'expired' in error_msg.lower():
                    logger.info("OAuth token may be expired, trying OpenRouter fallback")
                else:
                    # Other error, still try fallback
                    logger.info("Trying OpenRouter fallback after SDK error")

        # ========== METHOD 2: OpenRouter Fallback ==========
        # Uses Claude models via OpenRouter (supports vision)
        openrouter_key = os.getenv('OPENROUTER_API_KEY')
        if openrouter_key:
            try:
                import httpx

                # Build user message content with images for OpenRouter
                if comic_images:
                    # OpenRouter uses OpenAI-style multimodal format
                    user_content = []
                    for img in comic_images:
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{img['media_type']};base64,{img['data']}"
                            }
                        })
                    user_content.append({"type": "text", "text": request.message})
                else:
                    user_content = request.message

                async with httpx.AsyncClient(timeout=60.0) as http_client:
                    response = await http_client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {openrouter_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://collectibles-grading.local",
                            "X-Title": "Comic Grading Assistant"
                        },
                        json={
                            "model": "anthropic/claude-3.5-sonnet:beta",
                            "messages": [
                                {"role": "system", "content": system_prompt + "\n\n" + collection_context},
                                {"role": "user", "content": user_content}
                            ],
                            "max_tokens": 2000
                        }
                    )
                    if response.status_code == 200:
                        result_data = response.json()
                        fallback_text = result_data['choices'][0]['message']['content']
                        logger.info("OpenRouter fallback succeeded")
                        return {
                            'success': True,
                            'response': fallback_text,
                            'usage': {
                                'method': 'openrouter_fallback',
                                'cost': 'OpenRouter credits',
                                'model': 'claude-3.5-sonnet'
                            }
                        }
                    else:
                        logger.error(f"OpenRouter returned {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"OpenRouter fallback failed: {e}")

        # No methods worked
        return {
            'success': False,
            'response': "Unable to connect to Claude. Please check your OAuth token or OpenRouter API key.",
            'error': 'no_api_available',
            'needs_auth': True
        }

    except Exception as e:
        logger.error(f"Claude chat error: {e}")
        return {
            'success': False,
            'response': f"Sorry, I encountered an error: {str(e)}",
            'error': str(e)
        }


@app.post("/grade/{comic_id}", response_model=APIResponse)
async def grade_comic(
    comic_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    force_regrade: bool = Query(False),
    include_pricing: bool = Query(True),
    user: dict = Depends(require_grader),
    rate_limit: dict = Depends(check_rate_limit("grade", 10, 3600))  # 10 grades per hour
):
    """
    Grade a comic using AI consensus

    Requires grader or admin role. Rate limited to 10 grades per hour.
    """
    # Audit the grading request
    await audit_logger.log(
        action="grade_comic",
        user_id=user.get('user_id'),
        resource="comic",
        resource_id=str(comic_id),
        ip_address=request.client.host if request.client else None
    )
    comic = db.get_comic(comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")

    if not comic.get('front_image_path'):
        raise HTTPException(status_code=400, detail="Front image required for grading")

    # Check if already graded
    if comic.get('consensus_grade') and not force_regrade:
        return APIResponse(
            success=True,
            message="Comic already graded (use force_regrade=true to regrade)",
            data={"grade": comic['consensus_grade']}
        )

    # Perform grading
    try:
        grade_result = await consensus_grader.grade_comic(
            front_image=comic['front_image_path'],
            back_image=comic.get('back_image_path'),
            metadata={
                'title': comic.get('title'),
                'publisher': comic.get('publisher'),
                'key_issue': comic.get('key_issue')
            }
        )

        # Update database
        db.update_grading(comic_id, grade_result)

        # Broadcast to WebSocket clients
        await ws_manager.broadcast({
            "event": "grade_complete",
            "comic_id": comic_id,
            "grade": grade_result['consensus_grade']
        })

        # Get pricing if requested
        if include_pricing:
            background_tasks.add_task(
                _fetch_pricing,
                comic_id,
                comic['title'],
                comic.get('issue_number'),
                grade_result['consensus_grade']
            )

        return APIResponse(
            success=True,
            message="Grading complete",
            data=grade_result
        )

    except Exception as e:
        logger.error(f"Grading error for comic {comic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/grade/batch", response_model=BatchGradeResult)
async def batch_grade(
    request: Request,
    batch_request: BatchGradeRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_grader),
    rate_limit: dict = Depends(check_rate_limit("batch_grade", 5, 3600))  # 5 batch operations per hour
):
    """Batch grade multiple comics - requires grader role"""
    # Limit batch size
    if len(batch_request.comic_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 comics per batch")

    # Audit log
    await audit_logger.log(
        action="batch_grade",
        user_id=user.get('user_id') if user.get('type') == 'jwt' else None,
        api_key_id=user.get('key_id') if user.get('type') == 'api_key' else None,
        resource="batch",
        ip_address=request.client.host if request.client else None,
        details={"comic_count": len(batch_request.comic_ids)}
    )

    background_tasks.add_task(_batch_grade_task, batch_request)

    return BatchGradeResult(
        total=len(batch_request.comic_ids),
        successful=0,
        failed=0,
        results=[],
        errors=[],
        total_time_seconds=0
    )


async def _batch_grade_task(request: BatchGradeRequest):
    """Background batch grading task"""
    start_time = datetime.utcnow()
    total_comics = len(request.comic_ids)
    current_index = 0

    for comic_id in request.comic_ids:
        current_index += 1
        try:
            comic = db.get_comic(comic_id)
            if not comic or not comic.get('front_image_path'):
                continue

            grade_result = await consensus_grader.grade_comic(
                front_image=comic['front_image_path'],
                back_image=comic.get('back_image_path')
            )

            db.update_grading(comic_id, grade_result)

            # Send progress with full comic info for voice feedback
            await ws_manager.broadcast({
                "event": "batch_progress",
                "comic_id": comic_id,
                "title": comic.get('title', 'Comic'),
                "issue_number": comic.get('issue_number', ''),
                "grade": grade_result['consensus_grade'],
                "current": current_index,
                "total": total_comics
            })

        except Exception as e:
            logger.error(f"Batch grade error for comic {comic_id}: {e}")

    await ws_manager.broadcast({
        "event": "batch_complete",
        "total": total_comics
    })


async def _fetch_pricing(comic_id: int, title: str, issue_number: str, grade: float):
    """Background pricing fetch task"""
    try:
        logger.info(f"Fetching pricing for comic {comic_id}: {title} #{issue_number} grade {grade}")
        price_data = await pricing_engine.get_consensus_price(
            title=title,
            issue_number=issue_number,
            grade=grade
        )

        # Log the result
        consensus = price_data.get('consensus_price')
        sources = price_data.get('sources_used', 0)
        logger.info(f"Pricing result for comic {comic_id}: consensus=${consensus}, sources={sources}")

        # Log individual source results
        if price_data.get('gpa_price'):
            logger.info(f"  GPA: ${price_data['gpa_price'].get('price')}")
        if price_data.get('heritage_price'):
            logger.info(f"  Heritage: ${price_data['heritage_price'].get('price')}")
        if price_data.get('ebay_price'):
            logger.info(f"  eBay: ${price_data['ebay_price'].get('price')}")

        # Always update pricing (even with None to clear stale data)
        db.update_pricing(comic_id, price_data)
        logger.info(f"Updated pricing in database for comic {comic_id}")

        await ws_manager.broadcast({
            "event": "price_update",
            "comic_id": comic_id,
            "price": consensus
        })
    except Exception as e:
        logger.error(f"Pricing error for comic {comic_id}: {e}", exc_info=True)


# ============================================================================
# GRADE SELECTED COMICS - Batch Grade Specific IDs
# ============================================================================

class GradeSelectedRequest(BaseModel):
    """Request model for grading selected comics by ID"""
    comic_ids: List[int]

@app.post("/comics/grade-selected", response_model=APIResponse)
async def grade_selected_comics(
    request: GradeSelectedRequest,
    background_tasks: BackgroundTasks
):
    """
    Grade specific selected comics by their IDs.
    Runs in background and broadcasts progress via WebSocket.
    NO AUTH REQUIRED for local desktop use.
    """
    try:
        if not request.comic_ids:
            return APIResponse(
                success=False,
                message="No comics selected for grading",
                data={"total": 0, "started": 0}
            )

        if len(request.comic_ids) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 comics per batch")

        # Validate comic IDs exist and have images
        valid_ids = []
        for comic_id in request.comic_ids:
            comic = db.get_comic(comic_id)
            if comic and comic.get('front_image_path'):
                valid_ids.append(comic_id)

        if not valid_ids:
            return APIResponse(
                success=False,
                message="No valid comics with images found",
                data={"total": len(request.comic_ids), "started": 0}
            )

        # Start background grading
        background_tasks.add_task(_grade_selected_task, valid_ids)

        return APIResponse(
            success=True,
            message=f"Started grading {len(valid_ids)} comics in background",
            data={
                "total_requested": len(request.comic_ids),
                "started": len(valid_ids),
                "comic_ids": valid_ids
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting grade selected: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _grade_selected_task(comic_ids: List[int]):
    """Background task to grade selected comics"""
    for i, comic_id in enumerate(comic_ids):
        try:
            comic = db.get_comic(comic_id)
            if not comic:
                continue

            # Broadcast progress
            await ws_manager.broadcast({
                "event": "grade_selected_progress",
                "comic_id": comic_id,
                "title": comic.get('title'),
                "progress": i + 1,
                "total": len(comic_ids),
                "status": "grading"
            })

            # Grade the comic
            grade_result = await consensus_grader.grade_comic(
                front_image=comic['front_image_path'],
                back_image=comic.get('back_image_path')
            )

            # Update database with grade
            db.update_grading(comic_id, grade_result)

            # Fetch pricing after grading
            estimated_value = 0
            consensus_grade = grade_result.get('consensus_grade', 0)
            if consensus_grade > 0:
                try:
                    from pricing_sources.ebay_scraper import fetch_ebay_price
                    ebay_result = await asyncio.wait_for(
                        fetch_ebay_price(
                            title=comic.get('title', ''),
                            issue_number=str(comic.get('issue_number', '') or ''),
                            grade=consensus_grade
                        ),
                        timeout=15
                    )
                    if ebay_result and ebay_result.get('price'):
                        estimated_value = ebay_result['price']
                        db.update_comic(comic_id, {'estimated_value': estimated_value})
                        logger.info(f"[PRICING] Comic {comic_id}: ${estimated_value}")
                except Exception as pe:
                    logger.warning(f"[PRICING] Failed for comic {comic_id}: {pe}")

            # Broadcast completion
            await ws_manager.broadcast({
                "event": "grade_selected_complete",
                "comic_id": comic_id,
                "title": comic.get('title'),
                "grade": grade_result.get('consensus_grade'),
                "estimated_value": estimated_value,
                "progress": i + 1,
                "total": len(comic_ids)
            })

        except Exception as e:
            logger.error(f"Error grading comic {comic_id}: {e}")
            await ws_manager.broadcast({
                "event": "grade_selected_error",
                "comic_id": comic_id,
                "error": str(e),
                "progress": i + 1,
                "total": len(comic_ids)
            })

    # Broadcast batch complete
    await ws_manager.broadcast({
        "event": "grade_selected_batch_complete",
        "total": len(comic_ids)
    })


# ============================================================================
# UNIVERSAL COLLECTIBLE GRADING ENDPOINTS
# ============================================================================

class UniversalGradeRequest(BaseModel):
    """Request model for grading any collectible type"""
    image_base64: str
    collectible_type: str = "comics"  # comics, trading_cards, coins, stamps, vinyl, action_figures, video_games
    metadata: Optional[Dict[str, Any]] = None

@app.post("/grade/collectible", response_model=APIResponse)
async def grade_any_collectible(
    request: UniversalGradeRequest
):
    """
    Grade any type of collectible using AI vision.
    Supports: comics, trading_cards, coins, stamps, vinyl, action_figures, video_games
    NO AUTH REQUIRED for local desktop use.
    """
    valid_types = ["comics", "trading_cards", "baseball_cards", "sports_cards",
                   "coins", "stamps", "vinyl", "vinyl_records", "action_figures",
                   "toys", "video_games"]

    if request.collectible_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid collectible type. Valid types: {valid_types}"
        )

    try:
        # Use comic grader for comics (existing logic)
        if request.collectible_type == "comics":
            grade_result = await consensus_grader.grade_comic(
                front_image=request.image_base64,
                metadata=request.metadata
            )
        else:
            # Use universal grader for other types
            from ai_providers.universal_grader import grade_collectible
            grade_result = await grade_collectible(
                image_input=request.image_base64,
                collectible_type=request.collectible_type,
                metadata=request.metadata
            )

        return APIResponse(
            success=True,
            message=f"Graded {request.collectible_type} successfully",
            data=grade_result
        )
    except Exception as e:
        logger.error(f"Error grading collectible: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/grading/scales", response_model=APIResponse)
async def get_grading_scales():
    """Get grading scale information for all collectible types"""
    from ai_providers.universal_grader import GRADING_SCALES

    return APIResponse(
        success=True,
        message="Grading scales for all collectible types",
        data={
            "scales": GRADING_SCALES,
            "types": list(GRADING_SCALES.keys())
        }
    )


@app.get("/grading/standards/{collectible_type}", response_model=APIResponse)
async def get_grading_standards(collectible_type: str):
    """Get detailed grading standards for a specific collectible type"""
    from ai_providers.universal_grader import load_grading_standards

    standards = load_grading_standards(collectible_type)
    if not standards:
        raise HTTPException(status_code=404, detail=f"No grading standards found for {collectible_type}")

    return APIResponse(
        success=True,
        message=f"Grading standards for {collectible_type}",
        data=standards
    )


# ============================================================================
# PRICING ENDPOINTS
# ============================================================================

@app.post("/price/{comic_id}", response_model=APIResponse)
async def get_pricing(
    comic_id: int,
    request: Request,
    rate_limit: dict = Depends(check_rate_limit("pricing", 30, 3600))  # 30 pricing lookups per hour
):
    """Get pricing data for a comic - NO AUTH for local desktop use"""
    comic = db.get_comic(comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")

    if not comic.get('consensus_grade'):
        raise HTTPException(status_code=400, detail="Comic must be graded before pricing")

    try:
        price_data = await pricing_engine.get_consensus_price(
            title=comic['title'],
            issue_number=comic.get('issue_number'),
            grade=comic['consensus_grade']
        )

        db.update_pricing(comic_id, price_data)

        # Audit log (local use - no user)
        await audit_logger.log(
            action="get_pricing",
            user_id=None,
            api_key_id=None,
            resource="comic",
            resource_id=str(comic_id),
            ip_address=request.client.host if request.client else None
        )

        return APIResponse(
            success=True,
            message="Pricing retrieved",
            data=price_data
        )
    except Exception as e:
        logger.error(f"Pricing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HISTORY ENDPOINTS
# ============================================================================

@app.get("/comics/{comic_id}/history/grading", response_model=APIResponse)
async def get_grading_history(
    comic_id: int,
    user: dict = Depends(require_auth)
):
    """Get grading history for a comic - requires authentication"""
    history = db.get_grading_history(comic_id)
    return APIResponse(success=True, data=history)


@app.get("/comics/{comic_id}/history/pricing", response_model=APIResponse)
async def get_pricing_history(
    comic_id: int,
    user: dict = Depends(require_auth)
):
    """Get pricing history for a comic - requires authentication"""
    history = db.get_pricing_history(comic_id)
    return APIResponse(success=True, data=history)


# ============================================================================
# LIVE PRICE UPDATE ENDPOINTS
# ============================================================================

@app.get("/prices/status", response_model=APIResponse)
async def get_price_update_status():
    """Get current price update scheduler status"""
    status = get_price_scheduler_status()
    return APIResponse(success=True, data=status)


@app.post("/prices/update", response_model=APIResponse)
async def trigger_price_update(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(default=50, ge=1, le=500),
    user: dict = Depends(require_auth)
):
    """Manually trigger a price update cycle"""
    if price_scheduler.is_running:
        return APIResponse(
            success=False,
            message="Price update already running",
            data=get_price_scheduler_status()
        )

    # Run price update in background
    background_tasks.add_task(run_price_updates, batch_size)
    logger.info(f"Price update triggered manually (batch_size={batch_size})")

    return APIResponse(
        success=True,
        message=f"Price update started for {batch_size} comics",
        data={"batch_size": batch_size, "status": "started"}
    )


@app.post("/prices/update/{comic_id}", response_model=APIResponse)
async def update_single_comic_price(
    comic_id: int,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_auth)
):
    """Update price for a single comic"""
    # Get comic from database
    comic = db.get_comic(comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")

    # Run update for this comic
    try:
        pricing_data = await price_scheduler.update_comic_prices(comic)
        if price_scheduler.save_pricing_data(comic_id, pricing_data):
            return APIResponse(
                success=True,
                message="Price updated successfully",
                data={
                    "comic_id": comic_id,
                    "ebay_sold_avg": pricing_data.get('ebay_sold', {}).get('avg_sold_price'),
                    "ebay_active_avg": pricing_data.get('ebay_active', {}).get('avg_asking_price'),
                    "cgc_estimate": pricing_data.get('cgc_estimate'),
                    "updated_at": pricing_data.get('updated_at')
                }
            )
        else:
            return APIResponse(success=False, message="Failed to save pricing data")
    except Exception as e:
        logger.error(f"Error updating price for comic {comic_id}: {e}")
        return APIResponse(success=False, message=str(e))


@app.get("/prices/comic/{comic_id}", response_model=APIResponse)
async def get_comic_prices(
    comic_id: int,
    user: dict = Depends(require_auth)
):
    """Get all pricing data for a comic including eBay data"""
    comic = db.get_comic(comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")

    # Parse ebay_price_data if it exists
    ebay_data = {}
    if comic.get('ebay_price_data'):
        try:
            ebay_data = json.loads(comic['ebay_price_data']) if isinstance(comic['ebay_price_data'], str) else comic['ebay_price_data']
        except:
            pass

    pricing_info = {
        "comic_id": comic_id,
        "title": comic.get('title'),
        "issue_number": comic.get('issue_number'),
        "grade": comic.get('consensus_grade'),
        "grade_label": get_grade_label(comic.get('consensus_grade', 7.0)),

        # Main price displays
        "graded_price": comic.get('consensus_price'),
        "ebay_sold_avg": ebay_data.get('ebay_sold', {}).get('avg_sold_price'),
        "ebay_active_avg": ebay_data.get('ebay_active', {}).get('avg_asking_price'),

        # Price range
        "price_range_low": comic.get('price_range_low'),
        "price_range_high": comic.get('price_range_high'),

        # Market info
        "market_trend": comic.get('market_trend', 'stable'),
        "pricing_confidence": comic.get('pricing_confidence', 0),

        # Detailed eBay data
        "ebay_sold": ebay_data.get('ebay_sold', {}),
        "ebay_active": ebay_data.get('ebay_active', {}),

        # CGC estimate
        "cgc_estimate": ebay_data.get('cgc_estimate'),

        # Last updated
        "last_priced": comic.get('last_priced')
    }

    return APIResponse(success=True, data=pricing_info)


@app.get("/prices/summary", response_model=APIResponse)
async def get_pricing_summary(
    user: dict = Depends(require_auth)
):
    """Get summary of catalog pricing status"""
    conn = db.get_connection()
    c = conn.cursor()

    # Get counts
    c.execute("SELECT COUNT(*) FROM comics WHERE consensus_grade IS NOT NULL")
    total_graded = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM comics WHERE consensus_price IS NOT NULL")
    total_priced = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM comics WHERE last_priced IS NULL AND consensus_grade IS NOT NULL")
    needs_pricing = c.fetchone()[0]

    c.execute("SELECT SUM(consensus_price) FROM comics WHERE consensus_price IS NOT NULL")
    total_value = c.fetchone()[0] or 0

    c.execute("SELECT AVG(consensus_price) FROM comics WHERE consensus_price IS NOT NULL")
    avg_price = c.fetchone()[0] or 0

    # Get price distribution
    c.execute("""
        SELECT
            CASE
                WHEN consensus_price < 50 THEN 'Under $50'
                WHEN consensus_price < 100 THEN '$50-100'
                WHEN consensus_price < 250 THEN '$100-250'
                WHEN consensus_price < 500 THEN '$250-500'
                WHEN consensus_price < 1000 THEN '$500-1000'
                ELSE 'Over $1000'
            END as price_tier,
            COUNT(*) as count
        FROM comics
        WHERE consensus_price IS NOT NULL
        GROUP BY price_tier
        ORDER BY MIN(consensus_price)
    """)
    price_distribution = {row[0]: row[1] for row in c.fetchall()}

    conn.close()

    return APIResponse(success=True, data={
        "total_graded": total_graded,
        "total_priced": total_priced,
        "needs_pricing": needs_pricing,
        "total_collection_value": round(total_value, 2),
        "average_price": round(avg_price, 2),
        "price_distribution": price_distribution,
        "scheduler_status": get_price_scheduler_status()
    })


# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================

@app.post("/export", response_model=APIResponse)
async def export_comics(
    request: Request,
    export_request: ExportRequest,
    user: dict = Depends(require_auth),
    rate_limit: dict = Depends(check_rate_limit("export", 10, 3600))  # 10 exports per hour
):
    """Export comics for investor portal - requires authentication"""
    comics = db.get_comics_for_export(export_request.comic_ids)

    if not comics:
        raise HTTPException(status_code=404, detail="No comics found for export")

    # Audit log
    await audit_logger.log(
        action="export_comics",
        user_id=user.get('user_id') if user.get('type') == 'jwt' else None,
        api_key_id=user.get('key_id') if user.get('type') == 'api_key' else None,
        resource="export",
        ip_address=request.client.host if request.client else None,
        details={"format": export_request.format, "count": len(comics)}
    )

    if export_request.format == "json":
        return APIResponse(success=True, data=comics)

    elif export_request.format == "csv":
        # Generate CSV
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=comics[0].keys())
        writer.writeheader()
        writer.writerows(comics)

        return JSONResponse(
            content={"csv_data": output.getvalue()},
            headers={"Content-Disposition": "attachment; filename=comics_export.csv"}
        )

    else:  # HTML
        # Trigger portal generation
        return APIResponse(
            success=True,
            message="HTML export triggered",
            data={"comic_count": len(comics)}
        )


@app.post("/publish", response_model=APIResponse)
async def publish_to_portal(
    comic_ids: List[int],
    request: Request,
    user: dict = Depends(require_grader)
):
    """Mark comics as published to investor portal - requires grader role"""
    count = db.mark_as_published(comic_ids)

    # Audit log
    await audit_logger.log(
        action="publish_comics",
        user_id=user.get('user_id') if user.get('type') == 'jwt' else None,
        api_key_id=user.get('key_id') if user.get('type') == 'api_key' else None,
        resource="publish",
        ip_address=request.client.host if request.client else None,
        details={"count": count}
    )

    return APIResponse(
        success=True,
        message=f"{count} comics published to portal"
    )


# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            # Handle incoming messages
            if data.get("action") == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.websocket("/ws/grading")
async def websocket_grading(websocket: WebSocket):
    """WebSocket for real-time grading feedback"""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "start_grading":
                comic_id = data.get("comic_id")
                if comic_id:
                    # Send progress updates during grading
                    await websocket.send_json({
                        "event": "grading_started",
                        "comic_id": comic_id
                    })

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ============================================================================
# MANUAL REVIEW ENDPOINTS
# ============================================================================

@app.get("/review/pending", response_model=APIResponse)
async def get_pending_reviews():
    """Get comics pending manual review (local app - no auth required)"""
    query = ComicSearchQuery(needs_manual_review=True, limit=100)
    results, total = db.search_comics(query.model_dump())
    return APIResponse(success=True, data={"comics": results, "total": total})


@app.post("/review/{comic_id}", response_model=APIResponse)
async def submit_manual_review(
    comic_id: int,
    request: Request,
    grade: float = Query(..., ge=0.0, le=10.0),
    notes: str = Query(None)
):
    """Submit manual grade review (local app - no auth required)"""
    comic = db.get_comic(comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")

    # Validate notes if provided
    if notes and input_validator.check_xss(notes):
        raise HTTPException(status_code=400, detail="Invalid characters in notes")

    db.update_comic(comic_id, {
        "consensus_grade": grade,
        "requires_manual_review": False,
        "review_reason": None,
        "grader_notes": notes
    })

    # Audit log
    await audit_logger.log(
        action="manual_review",
        user_id=None,
        api_key_id=None,
        resource="comic",
        resource_id=str(comic_id),
        ip_address=request.client.host if request.client else None,
        details={"grade": grade}
    )

    return APIResponse(success=True, message="Manual review submitted")


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.post("/admin/cleanup")
async def cleanup_old_data(
    request: Request,
    days: int = Query(90, ge=1, le=365),
    user: dict = Depends(require_admin)
):
    """Clean up old history data - requires admin role"""
    db.cleanup_old_history(days)

    # Audit log
    await audit_logger.log(
        action="admin_cleanup",
        user_id=user.get('user_id') if user.get('type') == 'jwt' else None,
        ip_address=request.client.host if request.client else None,
        details={"days": days}
    )

    return APIResponse(success=True, message=f"Cleaned up data older than {days} days")


@app.post("/admin/optimize")
async def optimize_database(
    request: Request,
    user: dict = Depends(require_admin)
):
    """Optimize database - requires admin role"""
    db.vacuum()

    # Audit log
    await audit_logger.log(
        action="admin_optimize",
        user_id=user.get('user_id') if user.get('type') == 'jwt' else None,
        ip_address=request.client.host if request.client else None
    )

    return APIResponse(success=True, message="Database optimized")


# ============================================================================
# VAULT STATUS ENDPOINTS
# ============================================================================

@app.get("/vault/status", response_model=APIResponse)
async def get_vault_status(
    user: dict = Depends(require_admin)
):
    """Get Promethian Vault connection status - requires admin role"""
    vault = get_vault()
    status = vault.get_vault_status()
    return APIResponse(success=True, data=status)


@app.get("/vault/providers", response_model=APIResponse)
async def get_configured_providers(
    user: dict = Depends(require_admin)
):
    """Get list of AI providers with configured API keys - requires admin role"""
    config_loader = get_config_loader()
    providers = config_loader.get_enabled_providers()

    provider_status = {}
    for provider in ['anthropic', 'google', 'openrouter', 'huggingface', 'gocollect', 'heritage', 'ebay']:
        config = config_loader.get_provider_config(provider)
        if config:
            provider_status[provider] = {
                'enabled': config.enabled,
                'has_key': bool(config.api_key),
                'model': config.model if hasattr(config, 'model') else None,
                'weight': config.weight if hasattr(config, 'weight') else None
            }

    return APIResponse(
        success=True,
        data={
            'enabled_providers': providers,
            'provider_status': provider_status
        }
    )


@app.post("/vault/reload", response_model=APIResponse)
async def reload_vault_config(
    request: Request,
    user: dict = Depends(require_admin)
):
    """Reload configuration from Promethian Vault - requires admin role"""
    vault = get_vault()
    vault.clear_cache()

    config_loader = get_config_loader()
    config_loader.reload_all()

    status = vault.get_vault_status()
    enabled = config_loader.get_enabled_providers()

    # Audit log
    await audit_logger.log(
        action="vault_reload",
        user_id=user.get('user_id') if user.get('type') == 'jwt' else None,
        ip_address=request.client.host if request.client else None
    )

    return APIResponse(
        success=True,
        message="Vault configuration reloaded",
        data={
            'vault_status': status,
            'enabled_providers': enabled
        }
    )


# ============================================================================
# COLLECTION MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/collections", response_model=APIResponse)
async def get_collections(
    include_inactive: bool = Query(False)
):
    """Get all collections"""
    collections = db.get_all_collections(include_inactive)
    return APIResponse(success=True, data={"collections": collections})


@app.get("/collections/types", response_model=APIResponse)
async def get_collection_types():
    """Get available collection types (comics, baseball cards, etc.)"""
    types = db.get_collection_types()
    return APIResponse(success=True, data={"types": types})


@app.get("/collections/default", response_model=APIResponse)
async def get_default_collection():
    """Get the default/active collection"""
    collection = db.get_default_collection()
    if not collection:
        # Create a default collection if none exists
        default_id = db.create_collection({
            'name': 'My Comics',
            'collection_type': 'comics',
            'description': 'Default comic book collection',
            'icon': '📚',
            'is_default': True
        })
        collection = db.get_collection(default_id)
    return APIResponse(success=True, data=collection)


@app.get("/collections/{collection_id}", response_model=APIResponse)
async def get_collection(
    collection_id: int
):
    """Get collection by ID"""
    collection = db.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return APIResponse(success=True, data=collection)


@app.post("/collections", response_model=APIResponse)
async def create_collection(
    data: Dict[str, Any],
    request: Request
):
    """Create a new collection"""
    try:
        # Validate required fields
        if not data.get('name'):
            raise HTTPException(status_code=400, detail="Collection name is required")

        # Validate input
        for key, value in data.items():
            if isinstance(value, str):
                if input_validator.check_sql_injection(value):
                    raise HTTPException(status_code=400, detail=f"Invalid characters in {key}")
                if input_validator.check_xss(value):
                    raise HTTPException(status_code=400, detail=f"Invalid characters in {key}")

        collection_id = db.create_collection(data)

        # Audit log
        await audit_logger.log(
            action="create_collection",
            resource="collection",
            resource_id=str(collection_id),
            ip_address=request.client.host if request.client else None
        )

        return APIResponse(
            success=True,
            message="Collection created successfully",
            data={"id": collection_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/collections/{collection_id}", response_model=APIResponse)
async def update_collection(
    collection_id: int,
    data: Dict[str, Any],
    request: Request
):
    """Update collection"""
    if not db.get_collection(collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")

    # Validate input
    for key, value in data.items():
        if isinstance(value, str):
            if input_validator.check_sql_injection(value):
                raise HTTPException(status_code=400, detail=f"Invalid characters in {key}")
            if input_validator.check_xss(value):
                raise HTTPException(status_code=400, detail=f"Invalid characters in {key}")

    db.update_collection(collection_id, data)

    # Audit log
    await audit_logger.log(
        action="update_collection",
        resource="collection",
        resource_id=str(collection_id),
        ip_address=request.client.host if request.client else None
    )

    return APIResponse(success=True, message="Collection updated successfully")


@app.delete("/collections/{collection_id}", response_model=APIResponse)
async def delete_collection(
    collection_id: int,
    request: Request,
    move_items_to: int = Query(None, description="Move items to this collection before deleting")
):
    """Delete collection"""
    collection = db.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    if collection.get('is_default'):
        raise HTTPException(status_code=400, detail="Cannot delete the default collection")

    if not db.delete_collection(collection_id, move_items_to):
        raise HTTPException(status_code=400, detail="Failed to delete collection")

    # Audit log
    await audit_logger.log(
        action="delete_collection",
        resource="collection",
        resource_id=str(collection_id),
        ip_address=request.client.host if request.client else None
    )

    return APIResponse(success=True, message="Collection deleted successfully")


@app.post("/collections/{collection_id}/set-default", response_model=APIResponse)
async def set_default_collection(
    collection_id: int,
    request: Request
):
    """Set a collection as the default/active collection"""
    if not db.get_collection(collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")

    db.set_default_collection(collection_id)

    # Audit log
    await audit_logger.log(
        action="set_default_collection",
        resource="collection",
        resource_id=str(collection_id),
        ip_address=request.client.host if request.client else None
    )

    return APIResponse(success=True, message="Default collection updated")


@app.get("/collections/{collection_id}/stats", response_model=APIResponse)
async def get_collection_stats(
    collection_id: int
):
    """Get statistics for a specific collection"""
    if not db.get_collection(collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")

    stats = db.get_collection_statistics(collection_id)
    return APIResponse(success=True, data=stats)


@app.post("/collections/{collection_id}/move-items", response_model=APIResponse)
async def move_items_to_collection(
    collection_id: int,
    item_ids: List[int],
    request: Request
):
    """Move items to a collection"""
    if not db.get_collection(collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")

    count = db.move_items_to_collection(item_ids, collection_id)

    # Update collection stats
    db.update_collection_stats(collection_id)

    # Audit log
    await audit_logger.log(
        action="move_items",
        resource="collection",
        resource_id=str(collection_id),
        ip_address=request.client.host if request.client else None,
        details={"items_moved": count}
    )

    return APIResponse(success=True, message=f"{count} items moved to collection")


# ============================================================================
# ANALYTICS & P&L ENDPOINTS
# ============================================================================

@app.get("/analytics/summary", response_model=APIResponse)
async def get_analytics_summary(
    collection_id: Optional[int] = Query(None),
    request: Request = None
):
    """Get analytics summary with investment totals, current value, and P&L"""
    try:
        # Get items with buy/sell data
        query_filter = {}
        if collection_id:
            query_filter['collection_id'] = collection_id

        conn = db._get_connection()
        c = conn.cursor()

        # Total invested (sum of buy_price for unsold items)
        if collection_id:
            c.execute("""
                SELECT
                    COALESCE(SUM(buy_price), 0) as total_invested,
                    COUNT(*) as items_with_cost
                FROM comics
                WHERE buy_price IS NOT NULL
                AND sold_price IS NULL
                AND collection_id = ?
            """, (collection_id,))
        else:
            c.execute("""
                SELECT
                    COALESCE(SUM(buy_price), 0) as total_invested,
                    COUNT(*) as items_with_cost
                FROM comics
                WHERE buy_price IS NOT NULL
                AND sold_price IS NULL
            """)

        invested_row = c.fetchone()
        total_invested = invested_row[0] if invested_row else 0
        items_with_cost = invested_row[1] if invested_row else 0

        # Current market value (sum of consensus_price for unsold items)
        if collection_id:
            c.execute("""
                SELECT COALESCE(SUM(consensus_price), 0) as current_value
                FROM comics
                WHERE consensus_price IS NOT NULL
                AND sold_price IS NULL
                AND collection_id = ?
            """, (collection_id,))
        else:
            c.execute("""
                SELECT COALESCE(SUM(consensus_price), 0) as current_value
                FROM comics
                WHERE consensus_price IS NOT NULL
                AND sold_price IS NULL
            """)

        value_row = c.fetchone()
        current_value = value_row[0] if value_row else 0

        # Total sales (sum of sold_price - fees)
        if collection_id:
            c.execute("""
                SELECT
                    COALESCE(SUM(sold_price), 0) as gross_sales,
                    COALESCE(SUM(sold_price - COALESCE(fees_paid, 0) - COALESCE(shipping_cost, 0)), 0) as net_sales,
                    COALESCE(SUM(buy_price), 0) as cost_of_sold,
                    COUNT(*) as items_sold
                FROM comics
                WHERE sold_price IS NOT NULL
                AND collection_id = ?
            """, (collection_id,))
        else:
            c.execute("""
                SELECT
                    COALESCE(SUM(sold_price), 0) as gross_sales,
                    COALESCE(SUM(sold_price - COALESCE(fees_paid, 0) - COALESCE(shipping_cost, 0)), 0) as net_sales,
                    COALESCE(SUM(buy_price), 0) as cost_of_sold,
                    COUNT(*) as items_sold
                FROM comics
                WHERE sold_price IS NOT NULL
            """)

        sales_row = c.fetchone()
        gross_sales = sales_row[0] if sales_row else 0
        net_sales = sales_row[1] if sales_row else 0
        cost_of_sold = sales_row[2] if sales_row else 0
        items_sold = sales_row[3] if sales_row else 0

        # Calculate P&L
        realized_pnl = net_sales - cost_of_sold  # Profit from sold items
        unrealized_pnl = current_value - total_invested  # Paper profit on holdings
        total_pnl = realized_pnl + unrealized_pnl

        # Recent transactions (last 10 buys/sells)
        if collection_id:
            c.execute("""
                SELECT id, title, issue_number, buy_price, buy_date, sold_price, sold_date, consensus_price
                FROM comics
                WHERE (buy_date IS NOT NULL OR sold_date IS NOT NULL)
                AND collection_id = ?
                ORDER BY COALESCE(sold_date, buy_date) DESC
                LIMIT 10
            """, (collection_id,))
        else:
            c.execute("""
                SELECT id, title, issue_number, buy_price, buy_date, sold_price, sold_date, consensus_price
                FROM comics
                WHERE buy_date IS NOT NULL OR sold_date IS NOT NULL
                ORDER BY COALESCE(sold_date, buy_date) DESC
                LIMIT 10
            """)

        transactions = []
        for row in c.fetchall():
            transactions.append({
                'id': row[0],
                'title': row[1],
                'issue_number': row[2],
                'buy_price': row[3],
                'buy_date': row[4],
                'sold_price': row[5],
                'sold_date': row[6],
                'current_value': row[7],
                'type': 'sale' if row[5] else 'purchase'
            })

        conn.close()

        return APIResponse(
            success=True,
            data={
                'total_invested': round(total_invested, 2),
                'current_value': round(current_value, 2),
                'gross_sales': round(gross_sales, 2),
                'net_sales': round(net_sales, 2),
                'realized_pnl': round(realized_pnl, 2),
                'unrealized_pnl': round(unrealized_pnl, 2),
                'total_pnl': round(total_pnl, 2),
                'items_with_cost': items_with_cost,
                'items_sold': items_sold,
                'roi_percent': round((total_pnl / total_invested * 100), 2) if total_invested > 0 else 0,
                'recent_transactions': transactions
            }
        )

    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/pnl", response_model=APIResponse)
async def get_pnl_data(
    collection_id: Optional[int] = Query(None),
    include_sold: bool = Query(True),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    request: Request = None
):
    """Get P&L data for all items with buy prices"""
    try:
        conn = db._get_connection()
        c = conn.cursor()

        # Build query based on filters
        where_clauses = ["buy_price IS NOT NULL"]
        params = []

        if collection_id:
            where_clauses.append("collection_id = ?")
            params.append(collection_id)

        if not include_sold:
            where_clauses.append("sold_price IS NULL")

        where_sql = " AND ".join(where_clauses)

        # Get total count
        c.execute(f"SELECT COUNT(*) FROM comics WHERE {where_sql}", params)
        total = c.fetchone()[0]

        # Get items with P&L calculations
        query = f"""
            SELECT
                id, title, issue_number, publisher,
                consensus_grade, consensus_price,
                buy_price, buy_date, buy_source,
                sold_price, sold_date, sold_to, sold_platform,
                shipping_cost, fees_paid,
                front_image_path
            FROM comics
            WHERE {where_sql}
            ORDER BY COALESCE(sold_date, buy_date, created_at) DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        c.execute(query, params)

        items = []
        for row in c.fetchall():
            buy_price = row[6] or 0
            sold_price = row[9]
            current_value = row[5] or buy_price  # Use buy price if no market value
            fees = (row[13] or 0) + (row[14] or 0)

            if sold_price:
                # Realized P&L
                pnl = sold_price - buy_price - fees
                pnl_percent = ((sold_price - fees) / buy_price - 1) * 100 if buy_price > 0 else 0
                status = 'sold'
            else:
                # Unrealized P&L
                pnl = current_value - buy_price
                pnl_percent = (current_value / buy_price - 1) * 100 if buy_price > 0 else 0
                status = 'holding'

            items.append({
                'id': row[0],
                'title': row[1],
                'issue_number': row[2],
                'publisher': row[3],
                'grade': row[4],
                'current_value': round(current_value, 2),
                'buy_price': round(buy_price, 2),
                'buy_date': row[7],
                'buy_source': row[8],
                'sold_price': round(sold_price, 2) if sold_price else None,
                'sold_date': row[10],
                'sold_to': row[11],
                'sold_platform': row[12],
                'fees': round(fees, 2),
                'pnl': round(pnl, 2),
                'pnl_percent': round(pnl_percent, 2),
                'status': status,
                'image_path': row[15]
            })

        conn.close()

        return APIResponse(
            success=True,
            data={
                'items': items,
                'total': total,
                'limit': limit,
                'offset': offset
            }
        )

    except Exception as e:
        logger.error(f"Error getting P&L data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/comics/{comic_id}/transaction", response_model=APIResponse)
async def update_transaction_data(
    comic_id: int,
    data: Dict[str, Any],
    request: Request
):
    """Update buy/sell transaction data for a comic"""
    comic = db.get_comic(comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")

    # Validate allowed fields for transaction updates
    allowed_fields = [
        'buy_price', 'buy_date', 'buy_source',
        'sold_price', 'sold_date', 'sold_to', 'sold_platform',
        'shipping_cost', 'fees_paid'
    ]

    update_data = {}
    for key, value in data.items():
        if key in allowed_fields:
            # Validate string fields
            if isinstance(value, str):
                if input_validator.check_sql_injection(value):
                    raise HTTPException(status_code=400, detail=f"Invalid characters in {key}")
                if input_validator.check_xss(value):
                    raise HTTPException(status_code=400, detail=f"Invalid characters in {key}")
            update_data[key] = value

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid transaction fields provided")

    db.update_comic(comic_id, update_data)

    # Audit log
    await audit_logger.log(
        action="update_transaction",
        resource="comic",
        resource_id=str(comic_id),
        ip_address=request.client.host if request.client else None,
        details={"fields_updated": list(update_data.keys())}
    )

    return APIResponse(success=True, message="Transaction data updated successfully")


@app.get("/analytics/monthly", response_model=APIResponse)
async def get_monthly_analytics(
    collection_id: Optional[int] = Query(None),
    months: int = Query(12, ge=1, le=36),
    request: Request = None
):
    """Get monthly breakdown of purchases, sales, and P&L"""
    try:
        conn = db._get_connection()
        c = conn.cursor()

        # Get monthly purchases
        if collection_id:
            c.execute("""
                SELECT
                    strftime('%Y-%m', buy_date) as month,
                    COUNT(*) as purchases,
                    SUM(buy_price) as spent
                FROM comics
                WHERE buy_date IS NOT NULL
                AND buy_date >= date('now', ? || ' months')
                AND collection_id = ?
                GROUP BY strftime('%Y-%m', buy_date)
                ORDER BY month DESC
            """, (f'-{months}', collection_id))
        else:
            c.execute("""
                SELECT
                    strftime('%Y-%m', buy_date) as month,
                    COUNT(*) as purchases,
                    SUM(buy_price) as spent
                FROM comics
                WHERE buy_date IS NOT NULL
                AND buy_date >= date('now', ? || ' months')
                GROUP BY strftime('%Y-%m', buy_date)
                ORDER BY month DESC
            """, (f'-{months}',))

        purchases_by_month = {row[0]: {'purchases': row[1], 'spent': row[2]} for row in c.fetchall()}

        # Get monthly sales
        if collection_id:
            c.execute("""
                SELECT
                    strftime('%Y-%m', sold_date) as month,
                    COUNT(*) as sales,
                    SUM(sold_price) as revenue,
                    SUM(sold_price - COALESCE(buy_price, 0) - COALESCE(fees_paid, 0) - COALESCE(shipping_cost, 0)) as profit
                FROM comics
                WHERE sold_date IS NOT NULL
                AND sold_date >= date('now', ? || ' months')
                AND collection_id = ?
                GROUP BY strftime('%Y-%m', sold_date)
                ORDER BY month DESC
            """, (f'-{months}', collection_id))
        else:
            c.execute("""
                SELECT
                    strftime('%Y-%m', sold_date) as month,
                    COUNT(*) as sales,
                    SUM(sold_price) as revenue,
                    SUM(sold_price - COALESCE(buy_price, 0) - COALESCE(fees_paid, 0) - COALESCE(shipping_cost, 0)) as profit
                FROM comics
                WHERE sold_date IS NOT NULL
                AND sold_date >= date('now', ? || ' months')
                GROUP BY strftime('%Y-%m', sold_date)
                ORDER BY month DESC
            """, (f'-{months}',))

        sales_by_month = {row[0]: {'sales': row[1], 'revenue': row[2], 'profit': row[3]} for row in c.fetchall()}

        # Combine into monthly data
        all_months = set(list(purchases_by_month.keys()) + list(sales_by_month.keys()))
        monthly_data = []

        for month in sorted(all_months, reverse=True):
            purchase_data = purchases_by_month.get(month, {'purchases': 0, 'spent': 0})
            sales_data = sales_by_month.get(month, {'sales': 0, 'revenue': 0, 'profit': 0})

            monthly_data.append({
                'month': month,
                'purchases': purchase_data['purchases'],
                'spent': round(purchase_data['spent'] or 0, 2),
                'sales': sales_data['sales'],
                'revenue': round(sales_data['revenue'] or 0, 2),
                'profit': round(sales_data['profit'] or 0, 2)
            })

        conn.close()

        return APIResponse(
            success=True,
            data={'monthly': monthly_data}
        )

    except Exception as e:
        logger.error(f"Error getting monthly analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CGC INTEGRATION ENDPOINTS
# ============================================================================

@app.get("/cgc/status", response_model=APIResponse)
async def get_cgc_status():
    """Get CGC authentication status"""
    try:
        status = await cgc_status()
        return APIResponse(success=True, data=status)
    except Exception as e:
        logger.error(f"CGC status check error: {e}")
        return APIResponse(success=False, message=str(e), data={'authenticated': False})


@app.post("/cgc/login", response_model=APIResponse)
async def cgc_login_endpoint(
    data: Dict[str, Any],
    request: Request
):
    """Login to CGC account"""
    username = data.get('username')
    password = data.get('password')
    remember = data.get('remember', True)

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    try:
        result = await cgc_login(username, password, remember)

        # Audit log (don't log password)
        await audit_logger.log(
            action="cgc_login",
            resource="cgc",
            ip_address=request.client.host if request.client else None,
            details={'success': result.get('success', False)}
        )

        if result.get('success'):
            return APIResponse(success=True, message="Login successful", data=result)
        else:
            return APIResponse(success=False, message=result.get('error', 'Login failed'))

    except Exception as e:
        logger.error(f"CGC login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cgc/logout", response_model=APIResponse)
async def cgc_logout_endpoint(request: Request):
    """Logout from CGC"""
    try:
        result = await cgc_logout()

        await audit_logger.log(
            action="cgc_logout",
            resource="cgc",
            ip_address=request.client.host if request.client else None
        )

        return APIResponse(success=result.get('success', False), message=result.get('message', ''))

    except Exception as e:
        logger.error(f"CGC logout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cgc/verify/{cert_number}", response_model=APIResponse)
async def verify_cgc_cert(cert_number: str):
    """Verify a CGC certification number"""
    try:
        result = await cgc_verify(cert_number)

        if result.get('success'):
            return APIResponse(success=True, data=result.get('data'))
        else:
            return APIResponse(success=False, message=result.get('error', 'Verification failed'))

    except Exception as e:
        logger.error(f"CGC verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cgc/census", response_model=APIResponse)
async def get_cgc_census(
    title: str = Query(..., min_length=1),
    issue: Optional[str] = Query(None)
):
    """Get CGC census data for a comic"""
    try:
        result = await cgc_census(title, issue)

        if result.get('success'):
            return APIResponse(success=True, data=result)
        else:
            return APIResponse(success=False, message=result.get('error', 'Census lookup failed'))

    except Exception as e:
        logger.error(f"CGC census error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TRENDING PRICES & MARKET ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/market/trending", response_model=APIResponse)
async def get_trending_prices(
    category: Optional[str] = Query(None, description="Category: comics, cards, coins, etc."),
    limit: int = Query(20, ge=1, le=100)
):
    """Get trending prices from eBay sold listings aggregated across users"""
    try:
        conn = db._get_connection()
        c = conn.cursor()

        # Get recent price changes from our database
        # This aggregates data that could be shared across hobby shops
        if category:
            c.execute("""
                SELECT
                    title, issue_number, publisher, consensus_grade,
                    consensus_price, price_change_percent,
                    ebay_avg_price, ebay_price_date,
                    collection_type
                FROM comics
                WHERE collection_type = ?
                AND consensus_price IS NOT NULL
                ORDER BY ABS(COALESCE(price_change_percent, 0)) DESC
                LIMIT ?
            """, (category, limit))
        else:
            c.execute("""
                SELECT
                    title, issue_number, publisher, consensus_grade,
                    consensus_price, price_change_percent,
                    ebay_avg_price, ebay_price_date,
                    collection_type
                FROM comics
                WHERE consensus_price IS NOT NULL
                ORDER BY ABS(COALESCE(price_change_percent, 0)) DESC
                LIMIT ?
            """, (limit,))

        trending = []
        for row in c.fetchall():
            price_change = row[5] or 0
            trending.append({
                'title': row[0],
                'issue_number': row[1],
                'publisher': row[2],
                'grade': row[3],
                'current_price': row[4],
                'price_change_percent': round(price_change, 2),
                'trend': 'up' if price_change > 2 else ('down' if price_change < -2 else 'flat'),
                'ebay_price': row[6],
                'ebay_date': row[7],
                'category': row[8]
            })

        conn.close()

        return APIResponse(
            success=True,
            data={
                'trending': trending,
                'category': category,
                'source': 'aggregated_market_data'
            }
        )

    except Exception as e:
        logger.error(f"Trending prices error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/market/compare", response_model=APIResponse)
async def compare_prices(
    title: str = Query(...),
    issue: Optional[str] = Query(None),
    grade: Optional[float] = Query(None)
):
    """Compare prices across different sources (eBay, CGC, Beckett, PSA, etc.)"""
    try:
        # This endpoint would aggregate from multiple pricing sources
        comparison = {
            'title': title,
            'issue_number': issue,
            'grade': grade,
            'sources': {}
        }

        # Placeholder for pricing sources by category
        # Each category has different relevant pricing sources
        pricing_sources = {
            'comics': ['ebay', 'gpa', 'heritage', 'cgc', 'cbcs'],
            'cards': ['ebay', 'psa', 'bgs', 'sgc', 'beckett'],
            'coins': ['ebay', 'pcgs', 'ngc', 'heritage'],
            'stamps': ['ebay', 'pse', 'heritage'],
            'toys': ['ebay', 'afa', 'heritage'],
            'art': ['ebay', 'heritage', 'sothebys', 'christies']
        }

        # Get eBay price if available
        from pricing_sources.ebay_scraper import fetch_ebay_prices
        try:
            ebay_result = await fetch_ebay_prices(title, issue, grade or 9.4, 'comics')
            if ebay_result.get('price'):
                comparison['sources']['ebay'] = {
                    'price': ebay_result['price'],
                    'confidence': ebay_result.get('confidence', 0.7),
                    'last_updated': ebay_result.get('sale_date'),
                    'type': 'sold_listings'
                }
        except Exception as e:
            logger.debug(f"eBay price fetch failed: {e}")

        # Note: Other sources would be added similarly
        # This is the framework for multi-source price comparison

        comparison['available_sources'] = pricing_sources

        return APIResponse(success=True, data=comparison)

    except Exception as e:
        logger.error(f"Price comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pricing-sources", response_model=APIResponse)
async def get_pricing_sources():
    """Get all available pricing sources by category"""
    sources = {
        'comics': {
            'primary': [
                {'id': 'ebay', 'name': 'eBay Sold', 'type': 'marketplace', 'graded': False},
                {'id': 'gpa', 'name': 'GoCollect/GPA', 'type': 'guide', 'graded': True},
                {'id': 'heritage', 'name': 'Heritage Auctions', 'type': 'auction', 'graded': True}
            ],
            'grading_companies': [
                {'id': 'cgc', 'name': 'CGC Comics', 'type': 'grading'},
                {'id': 'cbcs', 'name': 'CBCS', 'type': 'grading'},
                {'id': 'pgx', 'name': 'PGX', 'type': 'grading'}
            ]
        },
        'trading_cards': {
            'primary': [
                {'id': 'ebay', 'name': 'eBay Sold', 'type': 'marketplace', 'graded': False},
                {'id': 'tcgplayer', 'name': 'TCGPlayer', 'type': 'marketplace', 'graded': False},
                {'id': 'pwcc', 'name': 'PWCC Auctions', 'type': 'auction', 'graded': True}
            ],
            'grading_companies': [
                {'id': 'psa', 'name': 'PSA', 'type': 'grading'},
                {'id': 'bgs', 'name': 'BGS/Beckett', 'type': 'grading'},
                {'id': 'sgc', 'name': 'SGC', 'type': 'grading'},
                {'id': 'cgc_cards', 'name': 'CGC Cards', 'type': 'grading'}
            ],
            'price_guides': [
                {'id': 'beckett', 'name': 'Beckett Price Guide', 'type': 'guide'}
            ]
        },
        'coins': {
            'primary': [
                {'id': 'ebay', 'name': 'eBay Sold', 'type': 'marketplace', 'graded': False},
                {'id': 'heritage', 'name': 'Heritage Auctions', 'type': 'auction', 'graded': True},
                {'id': 'greatcollections', 'name': 'Great Collections', 'type': 'auction', 'graded': True}
            ],
            'grading_companies': [
                {'id': 'pcgs', 'name': 'PCGS', 'type': 'grading'},
                {'id': 'ngc', 'name': 'NGC', 'type': 'grading'},
                {'id': 'anacs', 'name': 'ANACS', 'type': 'grading'}
            ],
            'price_guides': [
                {'id': 'greysheet', 'name': 'CDN/Greysheet', 'type': 'guide'},
                {'id': 'redbook', 'name': 'Red Book', 'type': 'guide'}
            ]
        },
        'stamps': {
            'primary': [
                {'id': 'ebay', 'name': 'eBay Sold', 'type': 'marketplace', 'graded': False},
                {'id': 'heritage', 'name': 'Heritage Auctions', 'type': 'auction', 'graded': True}
            ],
            'grading_companies': [
                {'id': 'pse', 'name': 'PSE', 'type': 'grading'},
                {'id': 'psg', 'name': 'PSG', 'type': 'grading'}
            ],
            'price_guides': [
                {'id': 'scott', 'name': 'Scott Catalog', 'type': 'guide'}
            ]
        },
        'toys': {
            'primary': [
                {'id': 'ebay', 'name': 'eBay Sold', 'type': 'marketplace', 'graded': False},
                {'id': 'heritage', 'name': 'Heritage Auctions', 'type': 'auction', 'graded': True}
            ],
            'grading_companies': [
                {'id': 'afa', 'name': 'AFA', 'type': 'grading'},
                {'id': 'cas', 'name': 'CAS', 'type': 'grading'}
            ]
        },
        'art': {
            'primary': [
                {'id': 'ebay', 'name': 'eBay Sold', 'type': 'marketplace', 'graded': False},
                {'id': 'heritage', 'name': 'Heritage Auctions', 'type': 'auction', 'graded': False},
                {'id': 'sothebys', 'name': "Sotheby's", 'type': 'auction', 'graded': False},
                {'id': 'christies', 'name': "Christie's", 'type': 'auction', 'graded': False}
            ],
            'authentication': [
                {'id': 'cgc_sig', 'name': 'CGC Signature Series', 'type': 'authentication'}
            ]
        },
        'signed_books': {
            'primary': [
                {'id': 'ebay', 'name': 'eBay Sold', 'type': 'marketplace', 'graded': False},
                {'id': 'abebooks', 'name': 'AbeBooks', 'type': 'marketplace', 'graded': False},
                {'id': 'heritage', 'name': 'Heritage Auctions', 'type': 'auction', 'graded': False}
            ],
            'authentication': [
                {'id': 'jsa', 'name': 'JSA', 'type': 'authentication'},
                {'id': 'beckett_auth', 'name': 'Beckett Authentication', 'type': 'authentication'},
                {'id': 'psa_dna', 'name': 'PSA/DNA', 'type': 'authentication'}
            ]
        }
    }

    return APIResponse(success=True, data=sources)


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
