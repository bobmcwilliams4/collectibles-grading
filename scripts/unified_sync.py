#!/usr/bin/env python3
"""
EPOCGS Unified Collection Sync
Keeps all platforms in sync:
- CPU (SQLite) -> Source of truth
- Website (JSON + images)
- iOS App (Firebase Firestore + Storage)

Run: python unified_sync.py
"""

import sqlite3
import json
import os
import sys
import base64
import shutil
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
SQLITE_DB = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/collectibles.db")
WEBSITE_JSON = Path("P:/SOVEREIGN_APPS/website/data/comics.json")
WEBSITE_IMAGES = Path("P:/SOVEREIGN_APPS/website/public/comics")
IMAGE_BASE = Path("X:/ECHO_PRIME/COLLECTIBLES_GRADING/images/captures")

# Firebase Config
FIREBASE_PROJECT = "echo-prime-ai"
STORAGE_BUCKET = "echo-prime-ai.firebasestorage.app"
FIREBASE_FUNCTION_URL = "https://us-central1-echo-prime-ai.cloudfunctions.net/importCollection"
ADMIN_SECRET = "BMC_COMMANDER_EPOCGS_2025"

# Google Cloud MCP Server
GCP_MCP_URL = "http://localhost:8380"

# Commander info
COMMANDER_USER_ID = "bmc_commander"

# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_comics_from_sqlite():
    """Fetch all graded comics from SQLite - the source of truth"""
    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, issue_number, publisher, publication_year,
               consensus_grade, grade_label, grade_confidence,
               front_grade, back_grade, consensus_price,
               price_range_low, price_range_high, market_trend,
               key_issue, key_issue_reason, variant_cover, variant_description,
               front_image_path, back_image_path, confirmed_defects, date_added
        FROM comics
        WHERE consensus_grade IS NOT NULL
        ORDER BY id ASC
    """)

    comics = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return comics


def parse_defects(defects_json):
    """Parse defects JSON safely"""
    if not defects_json:
        return []
    try:
        return json.loads(defects_json)
    except:
        return []

# =============================================================================
# IMAGE FUNCTIONS
# =============================================================================

def get_image_path(comic):
    """Get the actual image path, checking multiple locations"""
    front_path = comic.get('front_image_path')
    if not front_path:
        return None

    file_path = Path(front_path)
    if file_path.exists():
        return file_path

    # Try alternate path
    alt_path = IMAGE_BASE / file_path.name
    if alt_path.exists():
        return alt_path

    return None


def upload_image_to_firebase(image_path, comic_id):
    """Upload image to Firebase Storage via Google Cloud MCP"""
    if not image_path or not image_path.exists():
        return None

    try:
        # Upload via GCP MCP server - using file_path (local path)
        blob_name = f"collectibles/{COMMANDER_USER_ID}/{image_path.name}"

        response = requests.post(
            f"{GCP_MCP_URL}/storage/upload",
            json={
                "bucket": STORAGE_BUCKET,
                "blob_name": blob_name,
                "file_path": str(image_path)
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                # Construct public URL
                url = f"https://storage.googleapis.com/{STORAGE_BUCKET}/{blob_name}"
                return url

        return None
    except Exception as e:
        print(f"    Upload error: {e}")
        return None

# =============================================================================
# FIREBASE SYNC
# =============================================================================

def sync_to_firebase(comics, image_urls):
    """Sync comics to Firebase Firestore"""
    print("\n[2/3] Syncing to Firebase Firestore...")

    batch_size = 50
    total_imported = 0

    for i in range(0, len(comics), batch_size):
        batch = comics[i:i + batch_size]

        # Prepare batch with image URLs
        prepared_batch = []
        for comic in batch:
            defects = parse_defects(comic.get('confirmed_defects'))

            comic_data = {
                "title": comic.get('title', 'Unknown'),
                "issueNumber": comic.get('issue_number'),
                "publisher": comic.get('publisher'),
                "publicationYear": comic.get('publication_year'),
                "grade": comic.get('consensus_grade'),
                "gradeLabel": comic.get('grade_label'),
                "confidence": comic.get('grade_confidence'),
                "frontGrade": comic.get('front_grade'),
                "backGrade": comic.get('back_grade'),
                "estimatedValue": comic.get('consensus_price') or 0,
                "valueRange": {
                    "low": comic.get('price_range_low'),
                    "high": comic.get('price_range_high')
                },
                "marketTrend": comic.get('market_trend') or 'stable',
                "keyIssue": bool(comic.get('key_issue')),
                "keyIssueReason": comic.get('key_issue_reason'),
                "variantCover": bool(comic.get('variant_cover')),
                "variantDescription": comic.get('variant_description'),
                "defects": defects,
                "gradedAt": comic.get('date_added'),
            }

            # Add image URL if uploaded
            url = image_urls.get(comic['id'])
            if url:
                comic_data['imageUrl'] = url
                comic_data['frontImageUrl'] = url

            prepared_batch.append(comic_data)

        # Send to Firebase Function
        try:
            response = requests.post(
                FIREBASE_FUNCTION_URL,
                json={"data": {"comics": prepared_batch, "adminSecret": ADMIN_SECRET}},
                timeout=120
            )
            result = response.json()

            if result.get('result', {}).get('success'):
                imported = result['result']['imported']
                total_imported += imported
                print(f"  Batch {i // batch_size + 1}: {imported} comics")
            else:
                print(f"  Batch {i // batch_size + 1} error: {result}")
        except Exception as e:
            print(f"  Batch {i // batch_size + 1} failed: {e}")

    print(f"  Total synced to Firebase: {total_imported}")
    return total_imported

# =============================================================================
# WEBSITE SYNC
# =============================================================================

def sync_to_website(comics, image_urls):
    """Sync comics to website JSON and copy images"""
    print("\n[3/3] Syncing to Website...")

    total_value = 0
    website_comics = []

    for comic in comics:
        defects = parse_defects(comic.get('confirmed_defects'))

        # Copy image to website public folder
        image_url = None
        image_path = get_image_path(comic)

        if image_path and image_path.exists():
            dest = WEBSITE_IMAGES / image_path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(image_path, dest)
            image_url = f"/comics/{image_path.name}"

        website_comics.append({
            "id": comic['id'],
            "title": comic['title'],
            "issueNumber": comic['issue_number'],
            "publisher": comic['publisher'],
            "year": comic['publication_year'],
            "grade": comic['consensus_grade'],
            "gradeLabel": comic['grade_label'],
            "confidence": comic['grade_confidence'],
            "frontGrade": comic['front_grade'],
            "backGrade": comic['back_grade'],
            "estimatedValue": comic['consensus_price'] or 0,
            "valueRange": {
                "low": comic['price_range_low'],
                "high": comic['price_range_high']
            },
            "marketTrend": comic['market_trend'],
            "keyIssue": bool(comic['key_issue']),
            "keyIssueReason": comic['key_issue_reason'],
            "variant": bool(comic['variant_cover']),
            "variantDescription": comic['variant_description'],
            "imageUrl": image_url,
            "firebaseImageUrl": image_urls.get(comic['id']),  # Also include Firebase URL
            "defects": defects,
            "gradedAt": comic['date_added']
        })

        if comic['consensus_price']:
            total_value += comic['consensus_price']

    # Write JSON
    output = {
        "collectionName": "The Commander's Comic Reserve",
        "owner": "Commander Bobby Don McWilliams II",
        "totalCount": len(website_comics),
        "totalValue": total_value,
        "lastUpdated": datetime.now().isoformat(),
        "syncedPlatforms": ["cpu", "website", "firebase"],
        "comics": website_comics
    }

    WEBSITE_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(WEBSITE_JSON, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"  Synced {len(website_comics)} comics")
    print(f"  Total value: ${total_value:,.2f}")
    return len(website_comics), total_value

# =============================================================================
# MAIN SYNC
# =============================================================================

def check_gcp_mcp_server():
    """Check if Google Cloud MCP server is running"""
    try:
        response = requests.get(f"{GCP_MCP_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def upload_images_parallel(comics, max_workers=5):
    """Upload images to Firebase Storage in parallel"""
    print("\n[1.5/3] Uploading images to Firebase Storage...")

    image_urls = {}
    to_upload = []

    for comic in comics:
        image_path = get_image_path(comic)
        if image_path:
            to_upload.append((comic['id'], image_path))

    print(f"  Found {len(to_upload)} images to upload")

    uploaded = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(upload_image_to_firebase, path, cid): (cid, path)
            for cid, path in to_upload
        }

        for future in as_completed(futures):
            cid, path = futures[future]
            try:
                url = future.result()
                if url:
                    image_urls[cid] = url
                    uploaded += 1
                    if uploaded % 10 == 0:
                        print(f"    Uploaded {uploaded}/{len(to_upload)}...")
                else:
                    failed += 1
            except Exception as e:
                failed += 1

    print(f"  Uploaded: {uploaded}, Failed: {failed}")
    return image_urls


def main():
    print("=" * 70)
    print("EPOCGS UNIFIED COLLECTION SYNC")
    print("CPU (SQLite) -> Website + iOS App (Firebase)")
    print("=" * 70)

    # Check GCP MCP server
    print("\n[0/3] Checking Google Cloud MCP server...")
    if check_gcp_mcp_server():
        print("  MCP Server: ONLINE")
        upload_images = True
    else:
        print("  MCP Server: OFFLINE - Skipping image uploads")
        print("  Start it with: python -m uvicorn server:app --port 8380")
        upload_images = False

    # Step 1: Read from SQLite
    print("\n[1/3] Reading from SQLite (source of truth)...")
    comics = get_comics_from_sqlite()
    print(f"  Found {len(comics)} graded comics")

    # Step 1.5: Upload images (if MCP server available)
    image_urls = {}
    if upload_images:
        image_urls = upload_images_parallel(comics)

    # Step 2: Sync to Firebase
    firebase_count = sync_to_firebase(comics, image_urls)

    # Step 3: Sync to Website
    website_count, total_value = sync_to_website(comics, image_urls)

    # Summary
    print("\n" + "=" * 70)
    print("SYNC COMPLETE!")
    print("=" * 70)
    print(f"""
  Source (SQLite):     {len(comics)} comics
  Firebase Firestore:  {firebase_count} synced
  Website JSON:        {website_count} synced
  Images Uploaded:     {len(image_urls)} to Firebase Storage
  Total Value:         ${total_value:,.2f}

  Platforms Synced:
    [x] CPU (SQLite) - Source of truth
    [x] Website (JSON + local images)
    [x] iOS App (Firebase Firestore{' + Storage images' if image_urls else ''})
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
