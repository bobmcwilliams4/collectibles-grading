# Firebase Integration Setup for EPOCGS Desktop App

**Created:** 2026-01-06
**Author:** CLAUDE_SECONDARY
**Purpose:** Enable cloud sync between desktop app and echo-op.com website

---

## Overview

The desktop app now supports **dual-storage mode**:
- **SQLite** (primary, local storage)
- **Firestore** (cloud sync, optional)

This allows graded items to sync across:
- Desktop app (Windows, macOS, Linux)
- Web app (echo-op.com)
- Mobile app (iOS, Android)

---

## Installation

### 1. Install Firebase Admin SDK

```bash
pip install firebase-admin>=6.4.0
```

Or add to `requirements.txt`:
```
firebase-admin>=6.4.0
```

### 2. Get Firebase Credentials

Firebase service account credentials are already in the vault:

**Location:** `O:/ECHO_OMEGA_PRIME/.promethian_vault/firebase_echo_prime_service_account.json`

**Alternative locations:**
- `E:/ECHO_OMEGA_PRIME/.promethian_vault/firebase_echo_prime_service_account.json`
- `P:/SOVEREIGN_APPS/collectibles_grading_system/backend/config/firebase_credentials.json`

### 3. Configure Environment Variables (Optional)

If you want to use eBay and PriceCharting price research features:

```bash
# .env file
EBAY_APP_ID=your_ebay_app_id
PRICECHARTING_API_KEY=15b5e725f250cc1c191534f44edf8cd3de3783ad
```

**Note:** PriceCharting API key is already in the vault:
- `O:/ECHO_OMEGA_PRIME/.promethian_vault/pricecharting_api_key.txt`

---

## Usage

### Enable Cloud Sync

```python
from backend.firebase_integration import get_firebase

# Initialize Firebase (auto-finds credentials from vault)
firebase = get_firebase()

# Cloud sync is now enabled automatically
```

### Disable Cloud Sync (Offline Mode)

```python
from backend.firebase_integration import FirebaseIntegration

# Disable cloud sync for offline operation
firebase = FirebaseIntegration(enable_sync=False)
```

### Sync Graded Item to Cloud

```python
from backend.firebase_integration import sync_item_to_cloud
from backend.types import GradedItem, ItemType, ListingStatus

# Create graded item
item = GradedItem(
    id="item_123",
    owner_id="user_abc",
    item_type=ItemType.COMIC,
    title="Amazing Spider-Man #1",
    consensus_grade=9.4,
    grade_label="NEAR MINT",
    grade_confidence=0.92,
    defects=[],
    listing_status=ListingStatus.NOT_LISTED,
    price_verified=False
)

# Sync to Firestore
await sync_item_to_cloud(item)
```

### Migrate Existing SQLite Data

```python
from backend.firebase_integration import sync_from_local_db

# Get items from SQLite
sqlite_items = [...]  # Query from SQLite database

# Sync all to Firestore
stats = await sync_from_local_db(sqlite_items, owner_id="user_abc")

print(f"Created: {stats['created']}")
print(f"Updated: {stats['updated']}")
print(f"Failed: {stats['failed']}")
```

---

## New Features

### 1. Expanded Item Types

The desktop app now supports **8 item types** (was 1 - comics only):

| Type | Example |
|------|---------|
| `comic` | Amazing Spider-Man #1 |
| `card` | Pokemon Charizard 1st Edition |
| `coin` | 1909-S VDB Lincoln Penny |
| `stamp` | Inverted Jenny |
| `vinyl` | Beatles White Album |
| `toy` | Star Wars Boba Fett Action Figure |
| `gaming_system` | Nintendo 64 Console |
| `video_game` | The Legend of Zelda: Ocarina of Time |

### 2. AI Price Research

```python
from backend.price_research import research_market_price
from backend.types import ItemType

# Research market price
research = await research_market_price(
    item_title="The Legend of Zelda: Ocarina of Time N64 Gold Cartridge",
    item_type=ItemType.VIDEO_GAME,
    year=1998
)

print(f"eBay avg sold: ${research.ebay_avg_sold}")
print(f"PriceCharting value: ${research.price_charting_value}")
print(f"Suggested max price: ${research.suggested_max_price}")
```

### 3. Price Verification (Anti-Gouging)

```python
from backend.price_research import verify_price

# Check if proposed price is reasonable
verification = verify_price(
    proposed_price=85.00,
    market_research=research
)

if not verification['is_reasonable']:
    print(verification['warning'])
    # "Your price ($85.00) is 100% above market average ($42.50).
    #  Consider pricing at $63.75 or less for faster sales."
```

### 4. Marketplace Integration

```python
from backend.firebase_integration import get_firebase

firebase = get_firebase()

# Link graded item to marketplace listing
await firebase.link_to_marketplace(
    item_id="item_123",
    listing_id="listing_xyz"
)

# Item is now marked as LISTED with marketplace link
```

---

## Architecture

### Dual-Storage Pattern

```
┌─────────────────────────────────────────────────┐
│  Desktop App (Electron + Python)                │
├─────────────────────────────────────────────────┤
│                                                  │
│  SQLite (Primary)          Firestore (Cloud)    │
│  ├── collectibles.db       ├── graded_items     │
│  ├── Fast local access     ├── Real-time sync   │
│  ├── Offline support       ├── Cross-platform   │
│  └── Always available      └── Marketplace link │
│                                                  │
│  User can disable Firestore for offline mode    │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Cross-Platform Sync

```
Desktop App (SQLite + Firestore)
         │
         ▼
    Firebase Firestore ◄─── Web App (Next.js)
         │
         ▼
    Mobile App (React Native)
```

All platforms share the same Firestore collections:
- `graded_items`
- `user_collections`
- `marketplace` (extended with grading data)

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/types.py` | Expanded type system (8 item types) |
| `backend/firebase_integration.py` | Firestore CRUD + dual-storage |
| `backend/price_research.py` | eBay + PriceCharting API integration |
| `FIREBASE_SETUP.md` | This file - setup instructions |

---

## Testing

### Test Firebase Connection

```python
from backend.firebase_integration import get_firebase

firebase = get_firebase()

if firebase.enabled:
    print("✅ Firebase connected successfully")
else:
    print("❌ Firebase disabled (offline mode or credentials missing)")
```

### Test Price Research

```python
from backend.price_research import research_market_price_sync
from backend.types import ItemType

# Sync version (for non-async contexts)
research = research_market_price_sync(
    "Amazing Spider-Man #1",
    ItemType.COMIC,
    1963
)

print(f"Data sources: {research.data_sources}")
print(f"Average price: ${research.ebay_avg_sold}")
```

---

## Troubleshooting

### Firebase credentials not found

**Solution:** Ensure credentials exist in vault:
```bash
ls -la O:/ECHO_OMEGA_PRIME/.promethian_vault/firebase_echo_prime_service_account.json
```

### httpx not installed

**Solution:** Install httpx for price research:
```bash
pip install httpx>=0.26.0
```

### eBay/PriceCharting API errors

**Solution:** Set API keys in `.env` file or vault

---

## Next Steps

1. **Install firebase-admin:** `pip install firebase-admin`
2. **Test connection:** Run test script above
3. **Migrate existing data:** Use `sync_from_local_db()` function
4. **Enable in UI:** Add Firebase sync toggle to Electron app settings
5. **Deploy:** Build installers with Firebase support included

---

*Synced from web app on 2026-01-06 by CLAUDE_SECONDARY*
*ECHO OMEGA PRIME | Authority 11.0*
