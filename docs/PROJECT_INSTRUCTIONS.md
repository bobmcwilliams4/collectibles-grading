# Collectibles Grading System - Project Instructions

## Identity
You are assisting Commander Bobby Don McWilliams II (Authority Level 11.0) with the Collectibles Grading System - an AI-powered platform for authenticating, grading, and valuing collectibles.

## Project Location
X:\ECHO_PRIME\COLLECTIBLES_GRADING

## Core Technologies
- Python 3.11 (use PyManager: H:\Tools\PyManager\pythons\py311\python.exe)
- FastAPI backend (port 8000)
- Electron GUI
- SQLite database: collectibles.db
- 5 AI providers: Claude (35%), Gemini (25%), OpenRouter (20%), HuggingFace (15%), Local (5%)

## Key Files
- backend/main.py - FastAPI server (134KB)
- backend/ai_consensus.py - Multi-model voting
- backend/database.py - SQLite operations
- backend/pricing_engine.py - Price aggregation
- backend/catalog_export.py - Multi-format export tool
- electron-app/ - Desktop GUI
- webcam_module/ - Camera capture
- docs/CATALOGING_SKILL.md - Field reference for all collectible types
- config/catalog_templates.json - JSON templates

## Grading Standards
- Comics: CGC 0.5-10.0 scale
- Cards: PSA 1-10 scale
- Coins: Sheldon 1-70 (PCGS/NGC)
- 85% model agreement required for grade
- 2+ models must confirm each defect

## When Editing Code
- Edit originals only - NO _backup, _v2, _fixed copies
- Use GS343 + Phoenix integration for error handling
- Register new endpoints in main.py
- Test with: cd backend && uvicorn main:app --reload

## API Endpoints Pattern
GET /comics - List all
POST /comics - Add new
POST /grade/{id} - Grade item
POST /price/{id} - Get pricing
GET /stats - Analytics

## Voice Feedback
- Bree personality (bree_voice_feedback.py)
- ElevenLabs TTS integration
- Real-time capture guidance

## Pricing Sources
- GoCollect/GPA Analytics
- Heritage Auctions
- eBay sold listings (weighted average)

## Security
- API keys from Promethian Vault (X:\ECHO_PRIME\PROMETHEUS_PRIME\.promethian_vault)
- AES-256-GCM encryption
- Fallback to environment variables

## Output Goals
- Accurate pre-submission grade estimates
- Market value aggregation
- Static investor portal (Netlify deploy)
- Batch processing for bulk collections

## Communication Style
Direct, technical, execute-first. Minimal explanation unless requested.
