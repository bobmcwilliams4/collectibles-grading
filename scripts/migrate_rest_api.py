#!/usr/bin/env python3
"""
EPOCGS Collection Migration via Firebase REST API
Migrates comics from SQLite to Firestore using REST API (no service account needed)
"""

import sqlite3
import json
import os
import sys
import requests
import base64
from pathlib import Path
from datetime import datetime
import hashlib

# Firebase Config
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyCuTHwqo6HPjR0oSlCnWBkRslXTZg41VWY",
    "projectId": "echo-prime-ai",
    "storageBucket": "echo-prime-ai.firebasestorage.app",
}

# Commander's user ID
COMMANDER_USER_ID = "bmc_commander"

# Paths
SQLITE_DB = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/collectibles.db")
IMAGE_BASE = Path("X:/ECHO_PRIME/COLLECTIBLES_GRADING/images/captures")


def upload_image_to_storage(local_path: str) -> str:
    """Upload image to Firebase Storage via REST API and return public URL"""
    if not local_path:
        return None

    file_path = Path(local_path)
    if not file_path.exists():
        # Try alternate path
        file_path = IMAGE_BASE / file_path.name
        if not file_path.exists():
            print(f"    Image not found: {local_path}")
            return None

    try:
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()

        # Create unique filename
        file_hash = hashlib.md5(file_content).hexdigest()[:8]
        filename = f"collectibles/{COMMANDER_USER_ID}/{file_hash}_{file_path.name}"

        # Upload to Firebase Storage
        upload_url = f"https://firebasestorage.googleapis.com/v0/b/{FIREBASE_CONFIG['storageBucket']}/o?name={filename}"

        headers = {
            "Content-Type": "image/jpeg",
        }

        response = requests.post(upload_url, headers=headers, data=file_content)

        if response.status_code == 200:
            # Get download URL
            result = response.json()
            token = result.get('downloadTokens', '')
            download_url = f"https://firebasestorage.googleapis.com/v0/b/{FIREBASE_CONFIG['storageBucket']}/o/{filename.replace('/', '%2F')}?alt=media&token={token}"
            print(f"    Uploaded: {file_path.name}")
            return download_url
        else:
            print(f"    Upload failed ({response.status_code}): {file_path.name}")
            return None

    except Exception as e:
        print(f"    Upload error: {e}")
        return None


def add_to_firestore(doc_data: dict) -> str:
    """Add document to Firestore via REST API"""
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_CONFIG['projectId']}/databases/(default)/documents/collectibles"

    # Convert to Firestore format
    def to_firestore_value(val):
        if val is None:
            return {"nullValue": None}
        elif isinstance(val, bool):
            return {"booleanValue": val}
        elif isinstance(val, int):
            return {"integerValue": str(val)}
        elif isinstance(val, float):
            return {"doubleValue": val}
        elif isinstance(val, str):
            return {"stringValue": val}
        elif isinstance(val, list):
            return {"arrayValue": {"values": [to_firestore_value(v) for v in val]}}
        elif isinstance(val, dict):
            return {"mapValue": {"fields": {k: to_firestore_value(v) for k, v in val.items() if v is not None}}}
        else:
            return {"stringValue": str(val)}

    fields = {k: to_firestore_value(v) for k, v in doc_data.items() if v is not None}

    payload = {"fields": fields}

    headers = {
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        doc_id = result.get('name', '').split('/')[-1]
        return doc_id
    else:
        raise Exception(f"Firestore error ({response.status_code}): {response.text}")


def get_comics_from_sqlite():
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
               front_image_path, back_image_path, confirmed_defects,
               claude_grade_data, gemini_grade_data, date_added
        FROM comics
        WHERE consensus_grade IS NOT NULL
        ORDER BY id ASC
    """)

    comics = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return comics


def migrate_comic(comic: dict) -> str:
    """Migrate a single comic to Firebase"""

    # Upload images
    front_url = upload_image_to_storage(comic.get('front_image_path'))
    back_url = upload_image_to_storage(comic.get('back_image_path'))

    # Parse JSON fields
    def safe_json_parse(data):
        if not data:
            return None
        try:
            return json.loads(data)
        except:
            return None

    # Build document
    doc_data = {
        "userId": COMMANDER_USER_ID,
        "type": "comic",
        "source": "desktop_migration",
        "originalId": comic['id'],

        "title": comic.get('title', 'Unknown'),
        "issueNumber": comic.get('issue_number'),
        "publisher": comic.get('publisher'),
        "publicationYear": comic.get('publication_year'),

        "grade": comic.get('consensus_grade'),
        "gradeLabel": comic.get('grade_label'),
        "confidence": comic.get('grade_confidence'),
        "frontGrade": comic.get('front_grade'),
        "backGrade": comic.get('back_grade'),

        "estimatedValue": comic.get('consensus_price'),
        "valueRange": {
            "low": comic.get('price_range_low'),
            "high": comic.get('price_range_high'),
        },
        "marketTrend": comic.get('market_trend'),

        "keyIssue": bool(comic.get('key_issue')),
        "keyIssueReason": comic.get('key_issue_reason'),
        "variantCover": bool(comic.get('variant_cover')),
        "variantDescription": comic.get('variant_description'),

        "defects": safe_json_parse(comic.get('confirmed_defects')) or [],

        "imageUrl": front_url,
        "frontImageUrl": front_url,
        "backImageUrl": back_url,

        "aiGrades": {
            "claude": safe_json_parse(comic.get('claude_grade_data')),
            "gemini": safe_json_parse(comic.get('gemini_grade_data')),
        },

        "createdAt": datetime.utcnow().isoformat() + "Z",
        "gradedAt": comic.get('date_added'),
        "migratedAt": datetime.utcnow().isoformat() + "Z",
    }

    # Add to Firestore
    doc_id = add_to_firestore(doc_data)
    return doc_id


def main():
    print("=" * 60)
    print("EPOCGS Collection Migration to Firebase")
    print("=" * 60)

    # Get comics
    print("\n[1/2] Reading comics from SQLite...")
    comics = get_comics_from_sqlite()
    print(f"  Found {len(comics)} graded comics")

    # Migrate
    print(f"\n[2/2] Migrating to Firebase...")
    success = 0
    failed = 0

    for i, comic in enumerate(comics):
        title = comic.get('title', 'Unknown')
        issue = comic.get('issue_number', '')
        print(f"\n[{i+1}/{len(comics)}] {title} #{issue}")

        try:
            doc_id = migrate_comic(comic)
            print(f"  -> Created: {doc_id}")
            success += 1
        except Exception as e:
            print(f"  -> FAILED: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"  Success: {success}")
    print(f"  Failed:  {failed}")
    print(f"  Total:   {len(comics)}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
