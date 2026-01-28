#!/usr/bin/env python
"""
Clean Server Startup - Bypasses GS343/Phoenix auto-initialization
Prevents sys.modules corruption that breaks uvicorn imports
"""
import os
import sys

# CRITICAL: Disable all GS343/Phoenix auto-initialization BEFORE any imports
os.environ['GS343_DISABLE'] = '1'
os.environ['PHOENIX_DISABLE'] = '1'
os.environ['VAULT_DISABLE'] = '1'
os.environ['PYMANAGER_DISABLE_GS343'] = '1'

# Clear any corrupted sitecustomize effects
if hasattr(sys, 'warnoptions'):
    # Don't touch it, just verify it exists
    pass
else:
    # Restore warnoptions if missing
    sys.warnoptions = []

# Clean PYTHONPATH of any GS343 injection paths
pythonpath = os.environ.get('PYTHONPATH', '')
clean_paths = [p for p in pythonpath.split(';') if 'GS343' not in p.upper() and 'PROMETHEUS' not in p.upper()]
os.environ['PYTHONPATH'] = ';'.join(clean_paths)

# Now start uvicorn
if __name__ == '__main__':
    import uvicorn
    
    print("=" * 60)
    print("  COLLECTIBLES GRADING - CLEAN START")
    print("  GS343/Phoenix/Vault DISABLED for stability")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload to prevent re-initialization
        log_level="info"
    )
