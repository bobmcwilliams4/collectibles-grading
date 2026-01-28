#!/usr/bin/env python
"""
Server Launcher - Bypasses GS343 interference
Sets environment before any module imports
"""
import os
import sys

# Set environment variables BEFORE any imports that might trigger vault
os.environ['GS343_DISABLE'] = '1'
os.environ['PHOENIX_DISABLE'] = '1'
os.environ['VAULT_DISABLE'] = '1'
os.environ['SKIP_VAULT'] = '1'
os.environ['EPOCGS_DEV_MODE'] = 'true'

# Prevent any startup hooks
os.environ['PYTHONSTARTUP'] = ''
os.environ['PYTHONUSERBASE'] = ''

# Clear any corrupted sys.modules entries
keys_to_remove = [k for k in sys.modules.keys() if 'vault' in k.lower() or 'gs343' in k.lower()]
for k in keys_to_remove:
    del sys.modules[k]

print("[COLLECTIBLES GRADING] Environment configured")
print(f"  VAULT_DISABLE={os.environ.get('VAULT_DISABLE')}")
print(f"  EPOCGS_DEV_MODE={os.environ.get('EPOCGS_DEV_MODE')}")
print(f"  Python: {sys.version}")

# Now run uvicorn
if __name__ == '__main__':
    import uvicorn

    print("[COLLECTIBLES GRADING] Starting server on port 8000...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
