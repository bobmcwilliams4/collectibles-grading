"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║          CLAUDE OAUTH INTEGRATION INSTRUCTIONS - MAIN.PY                     ║
║           Commander Bobby Don McWilliams II - Authority Level 11.0           ║
╚═══════════════════════════════════════════════════════════════════════════════╝

INTEGRATION STEPS FOR MAIN.PY
"""

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: ADD IMPORTS (near top of file, after existing imports)
# ══════════════════════════════════════════════════════════════════════════════

from claude_oauth_manager import initialize_claude_auth, get_oauth_manager
from claude_chat_handler import get_chat_handler

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: INITIALIZE ON STARTUP (in @asynccontextmanager lifespan function)
# ══════════════════════════════════════════════════════════════════════════════

# Find the @asynccontextmanager decorated function (usually near line 100-150)
# Add this BEFORE the "yield" statement:

    # Initialize Claude OAuth (autonomous refresh)
    logger.info("Initializing Claude OAuth...")
    initialize_claude_auth()
    
# Example of where it goes:
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Startup and shutdown logic"""
#     # Existing startup code...
#     
#     # ADD THIS:
#     logger.info("Initializing Claude OAuth...")
#     initialize_claude_auth()
#     
#     yield  # <-- Must be BEFORE the yield
#     
#     # Shutdown code...

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: REPLACE claude_chat FUNCTION (around line 1252)
# ══════════════════════════════════════════════════════════════════════════════

# OLD VERSION (delete everything from @app.post("/claude/chat") to the end of the function)
# Replace with this:

@app.post("/claude/chat")
async def claude_chat(request: ClaudeChatRequest):
    """
    Chat with Claude about your comic collection.
    NOW WITH: Autonomous OAuth refresh + OpenRouter fallback!
    """
    try:
        # Get collection data for context
        comics_result = db.search_comics({})
        all_comics = comics_result[0] if comics_result else []
        stats = db.get_statistics()

        # Build context about the collection
        collection_context = f"""
You are a helpful comic book collection assistant. The user has a collection with:
- Total comics: {stats.get('total_comics', 0)}
- Total value: ${stats.get('total_value', 0):,.2f}
- Average grade: {stats.get('average_grade', 0):.1f}
- Publishers: {', '.join(stats.get('publishers', [])[:10])}

Recent comics in collection:
"""
        for comic in all_comics[:20]:
            title = comic.get('title', 'Unknown')
            issue = comic.get('issue_number', '?')
            grade = comic.get('consensus_grade', 'N/A')
            value = comic.get('estimated_value', 0)
            collection_context += f"- {title} #{issue} (Grade: {grade}, Value: ${value})\n"

        # Prepare system prompt based on context type
        if request.context == 'organize':
            system_prompt = """You are a comic collection organization expert.
Help the user organize their collection by suggesting categories, runs to complete,
and efficient storage/display strategies. Be specific and actionable."""
        elif request.context == 'analyze':
            system_prompt = """You are a comic market analyst and value expert.
Analyze the user's collection value, identify undervalued gems, suggest comics
that might appreciate, and provide market insights."""
        elif request.context == 'missing':
            system_prompt = """You are a comic run completion specialist.
Look at the user's collection and identify missing issues in runs,
key issues they should acquire, and affordable ways to complete sets."""
        else:
            system_prompt = """You are a friendly, knowledgeable comic book assistant.
Help the user with questions about their collection, grading, pricing,
and general comic book knowledge. Be concise but thorough."""

        # Use the new chat handler with automatic OAuth refresh + fallback
        handler = get_chat_handler()
        result = await handler.chat(
            message=request.message,
            system_prompt=system_prompt,
            context=collection_context,
            max_tokens=2000
        )

        if result['success']:
            return {
                'success': True,
                'response': result['response'],
                'usage': result.get('usage', {}),
                'method': result.get('method', 'unknown')
            }
        else:
            logger.error(f"Claude chat failed: {result.get('error')}")
            return {
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'method': result.get('method', 'unknown')
            }

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4: ADD HEALTH CHECK ENDPOINT (optional but recommended)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/claude/status")
async def claude_status():
    """Check Claude OAuth status"""
    manager = get_oauth_manager()
    creds = manager.get_credentials()
    
    if not creds:
        return {
            'oauth_configured': False,
            'token_valid': False,
            'subscription': None
        }
    
    oauth = creds.get('claudeAiOauth', {})
    is_expired = manager.is_token_expired()
    
    from datetime import datetime
    expires_at = oauth.get('expiresAt', 0)
    expires_dt = datetime.fromtimestamp(expires_at / 1000) if expires_at else None
    
    return {
        'oauth_configured': True,
        'token_valid': not is_expired,
        'subscription': oauth.get('subscriptionType', 'unknown'),
        'expires_at': expires_dt.isoformat() if expires_dt else None,
        'openrouter_available': bool(os.getenv('OPENROUTER_API_KEY'))
    }

# ══════════════════════════════════════════════════════════════════════════════
# TESTING
# ══════════════════════════════════════════════════════════════════════════════

"""
1. Start backend:
   python main.py

2. Check OAuth status:
   curl http://localhost:8000/claude/status

3. Test chat:
   curl -X POST http://localhost:8000/claude/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Tell me about my collection", "context": "general"}'

4. Watch logs for:
   - "✓ OAuth initialized successfully" on startup
   - "Token valid until: ..." with future date
   - "Using OpenRouter fallback" only if OAuth fails
"""
