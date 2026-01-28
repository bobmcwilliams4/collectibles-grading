# COLLECTIBLES GRADING SYSTEM - SOURCE MANIFEST

## Current Location

The Collectibles Grading System is currently located at:
- **Primary:** `X:\ECHO_PRIME\COLLECTIBLES_GRADING\`

### System Overview

| Component | Path | Description |
|-----------|------|-------------|
| Backend | backend/ | Flask API server, AI providers |
| Webcam Module | webcam_module/ | Camera capture, quality scoring |
| Electron App | electron-app/ | Desktop application |
| Launcher | launcher/ | System launcher |
| Static Export | static_export/ | Portal generation |

### AI Providers (backend/ai_providers/)

- openai_grader.py - OpenAI vision grading
- claude_grader.py - Claude vision grading
- gemini_grader.py - Gemini vision grading
- groq_grader.py - Groq fast grading
- ollama_vision_grader.py - Local Ollama grading
- universal_grader.py - Unified grading interface
- swarm_brain.py - Multi-AI consensus

### Voice Feedback

- raistlin_voice_feedback.py - Raistlin commentary
- bree_voice_feedback.py - Bree commentary
- collection_master_voice.py - Master voice

### Migration Status

| Component | Current | Target | Status |
|-----------|---------|--------|--------|
| Full System | X:\ECHO_PRIME\COLLECTIBLES_GRADING\ | P:\SOVEREIGN_APPS\collectibles_grading_system\ | REFERENCE CREATED |

### Commercialization Notes

- This is a **Tier 4** sellable asset
- Should consume ECHO as a service, not embed
- Has its own release cycle

---

**Created:** 2025-12-21 | **Authority:** Claude Code (9.5)
