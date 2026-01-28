#!/usr/bin/env python3
"""
EPOCGS Unified Collection Sync
Syncs SQLite collection to:
1. Firebase Firestore (iOS app)
2. Firebase Storage (images for app)
3. Website JSON (echo-op.com)
"""

import sqlite3
import json
import os
import sys
import requests
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Paths
SQLITE_DB = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/collectibles.db")
WEBSITE_JSON = Path("P:/SOVEREIGN_APPS/website/data/comics.json")
WEBSITE_IMAGES = Path("P:/SOVEREIGN_APPS/website/public/comics")
IMAGE_BASE = Path("X:/ECHO_PRIME/COLLECTIBLES_GRADING/images/captures")

# Firebase Config
FIREBASE_PROJECT = "echo-prime-ai"
STORAGE_BUCKET = "echo-prime-ai.firebasestorage.app"
FUNCTION_URL = "https://us-central1-echo-prime-ai.cloudfunctions.net/importCollection"
ADMIN_SECRET = "BMC_COMMANDER_EPOCGS_2025"


def get_comics():
    """Fetch all graded comics from SQLite"""
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


def upload_images_to_storage(comics):
    """Upload images to Firebase Storage using gsutil"""
    print("\n[2/4] Uploading images to Firebase Storage...")

    uploaded = 0
    failed = 0
    image_urls = {}

    for comic in comics:
        comic_id = comic['id']
        front_path = comic.get('front_image_path')
        back_path = comic.get('back_image_path')

        for img_type, local_path in [('front', front_path), ('back', back_path)]:
            if not local_path:
                continue

            file_path = Path(local_path)
            if not file_path.exists():
                # Try alternate path
                file_path = IMAGE_BASE / file_path.name
                if not file_path.exists():
                    continue

            # Upload using gsutil
            remote_path = f"gs://{STORAGE_BUCKET}/collectibles/bmc_commander/{file_path.name}"

            try:
                result = subprocess.run(
                    ["gsutil", "cp", str(file_path), remote_path],
                    capture_output=True, text=True, timeout=60
                )

                if result.returncode == 0:
                    # Generate public URL
                    public_url = f"https://firebasestorage.googleapis.com/v0/b/{STORAGE_BUCKET}/o/collectibles%2Fbmc_commander%2F{file_path.name}?alt=media"

                    if comic_id not in image_urls:
                        image_urls[comic_id] = {}
                    image_urls[comic_id][img_type] = public_url
                    uploaded += 1
                    print(f"  Uploaded: {file_path.name}")
                else:
                    failed += 1
                    print(f"  Failed: {file_path.name} - {result.stderr[:100]}")
            except Exception as e:
                failed += 1
                print(f"  Error: {file_path.name} - {e}")

    print(f"  Images uploaded: {uploaded}, Failed: {failed}")
    return image_urls


def sync_to_firebase(comics, image_urls):
    """Sync comics to Firebase Firestore via Cloud Function"""
    print("\n[3/4] Syncing to Firebase Firestore...")

    # Prepare comics with image URLs
    batch_size = 50
    total_imported = 0

    for i in range(0, len(comics), batch_size):
        batch = comics[i:i + batch_size]

        # Add image URLs to batch
        prepared_batch = []
        for comic in batch:
            # Parse defects
            defects = []
            if comic.get('confirmed_defects'):
                try:
                    defects = json.loads(comic['confirmed_defects'])
                except:
                    pass

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

            # Add image URLs if available
            urls = image_urls.get(comic['id'], {})
            if urls.get('front'):
                comic_data['imageUrl'] = urls['front']
                comic_data['frontImageUrl'] = urls['front']
            if urls.get('back'):
                comic_data['backImageUrl'] = urls['back']

            prepared_batch.append(comic_data)

        # Send to Firebase Function
        payload = {
            "data": {
                "comics": prepared_batch,
                "adminSecret": ADMIN_SECRET
            }
        }

        try:
            response = requests.post(FUNCTION_URL, json=payload, timeout=120)
            result = response.json()

            if result.get('result', {}).get('success'):
                imported = result['result']['imported']
                total_imported += imported
                print(f"  Batch {i // batch_size + 1}: {imported} comics imported")
            else:
                print(f"  Batch {i // batch_size + 1} error: {result}")
        except Exception as e:
            print(f"  Batch {i // batch_size + 1} failed: {e}")

    print(f"  Total synced to Firebase: {total_imported}")
    return total_imported


def sync_to_website(comics):
    """Sync comics to website JSON and copy images"""
    print("\n[4/4] Syncing to website...")

    total_value = 0
    website_comics = []

    for comic in comics:
        # Parse defects
        defects = []
        if comic.get('confirmed_defects'):
            try:
                defects = json.loads(comic['confirmed_defects'])
            except:
                pass

        # Copy image to website public folder
        image_url = None
        if comic.get('front_image_path'):
            img_path = Path(comic['front_image_path'])
            if not img_path.exists():
                img_path = IMAGE_BASE / img_path.name

            if img_path.exists():
                dest = WEBSITE_IMAGES / img_path.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(img_path, dest)
                image_url = f"/comics/{img_path.name}"

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
        "comics": website_comics
    }

    WEBSITE_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(WEBSITE_JSON, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"  Synced {len(website_comics)} comics to website")
    print(f"  Total value: ${total_value:,.2f}")
    return len(website_comics)


def main():
    print("=" * 60)
    print("EPOCGS UNIFIED COLLECTION SYNC")
    print("SQLite -> Firebase + Website")
    print("=" * 60)

    # Step 1: Read from SQLite
    print("\n[1/4] Reading comics from SQLite...")
    comics = get_comics()
    print(f"  Found {len(comics)} graded comics")

    # Step 2: Upload images to Firebase Storage
    image_urls = upload_images_to_storage(comics)

    # Step 3: Sync to Firebase Firestore
    firebase_count = sync_to_firebase(comics, image_urls)

    # Step 4: Sync to website
    website_count = sync_to_website(comics)

    # Summary
    print("\n" + "=" * 60)
    print("SYNC COMPLETE!")
    print("=" * 60)
    print(f"  Source:   {len(comics)} comics in SQLite")
    print(f"  Firebase: {firebase_count} synced to Firestore")
    print(f"  Website:  {website_count} synced to JSON")
    print(f"  Images:   {len(image_urls)} uploaded to Storage")

    return 0


if __name__ == "__main__":
    sys.exit(main())
