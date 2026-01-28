#!/usr/bin/env python3
"""
EPOCGS Collection Migration Script
Migrates existing comics from SQLite to Firebase (Firestore + Storage)
"""

import sqlite3
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, storage
import hashlib

# Firebase config
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyCuTHwqo6HPjR0oSlCnWBkRslXTZg41VWY",
    "authDomain": "echo-prime-ai.firebaseapp.com",
    "projectId": "echo-prime-ai",
    "storageBucket": "echo-prime-ai.firebasestorage.app",
}

# Commander's user ID (from Firebase Auth)
COMMANDER_USER_ID = "commander_bmc"  # Update with actual Firebase UID

# Paths
SQLITE_DB = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/collectibles.db")
SERVICE_ACCOUNT = Path("O:/ECHO_OMEGA_PRIME/config/firebase_service_account.json")


def init_firebase():
    """Initialize Firebase Admin SDK"""
    if not firebase_admin._apps:
        # Try service account first, fall back to default
        if SERVICE_ACCOUNT.exists():
            cred = credentials.Certificate(str(SERVICE_ACCOUNT))
            firebase_admin.initialize_app(cred, {
                'storageBucket': FIREBASE_CONFIG['storageBucket']
            })
        else:
            # Use application default credentials
            firebase_admin.initialize_app(options={
                'storageBucket': FIREBASE_CONFIG['storageBucket']
            })

    return firestore.client(), storage.bucket()


def get_comics_from_sqlite():
    """Fetch all comics from SQLite database"""
    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM comics
        WHERE consensus_grade IS NOT NULL
        ORDER BY date_added DESC
    """)

    comics = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return comics


def upload_image(bucket, local_path: str, user_id: str) -> str:
    """Upload image to Firebase Storage and return URL"""
    if not local_path or not Path(local_path).exists():
        return None

    try:
        local_file = Path(local_path)
        # Create unique filename based on content hash
        file_hash = hashlib.md5(local_file.read_bytes()).hexdigest()[:12]
        remote_path = f"collectibles/{user_id}/{file_hash}_{local_file.name}"

        blob = bucket.blob(remote_path)

        # Check if already uploaded
        if blob.exists():
            blob.make_public()
            return blob.public_url

        # Upload file
        blob.upload_from_filename(str(local_file))
        blob.make_public()

        print(f"  ✓ Uploaded: {local_file.name}")
        return blob.public_url
    except Exception as e:
        print(f"  ✗ Failed to upload {local_path}: {e}")
        return None


def migrate_comic(db, bucket, comic: dict, user_id: str) -> str:
    """Migrate a single comic to Firestore"""
    # Upload images
    front_url = upload_image(bucket, comic.get('front_image_path'), user_id)
    back_url = upload_image(bucket, comic.get('back_image_path'), user_id)

    # Parse JSON fields
    def safe_json_parse(data, default=None):
        if not data:
            return default
        try:
            return json.loads(data)
        except:
            return default

    # Build Firestore document
    doc_data = {
        # Core identification
        'userId': user_id,
        'type': 'comic',
        'source': 'desktop_migration',
        'originalId': comic['id'],

        # Item details
        'title': comic.get('title', 'Unknown'),
        'issueNumber': comic.get('issue_number'),
        'publisher': comic.get('publisher'),
        'publicationYear': comic.get('publication_year'),

        # Variant info
        'variantCover': bool(comic.get('variant_cover')),
        'variantDescription': comic.get('variant_description'),

        # Key issue
        'keyIssue': bool(comic.get('key_issue')),
        'keyIssueReason': comic.get('key_issue_reason'),

        # Grading data
        'grade': comic.get('consensus_grade'),
        'gradeLabel': comic.get('grade_label'),
        'confidence': comic.get('grade_confidence'),
        'frontGrade': comic.get('front_grade'),
        'backGrade': comic.get('back_grade'),
        'agreementPercentage': comic.get('agreement_percentage'),
        'standardDeviation': comic.get('standard_deviation'),
        'qualityAdjusted': bool(comic.get('quality_adjusted')),
        'qualityPenalty': comic.get('quality_penalty'),
        'requiresManualReview': bool(comic.get('requires_manual_review')),
        'reviewReason': comic.get('review_reason'),

        # Individual AI grades
        'aiGrades': {
            'claude': safe_json_parse(comic.get('claude_grade_data')),
            'gemini': safe_json_parse(comic.get('gemini_grade_data')),
            'openrouter': safe_json_parse(comic.get('openrouter_grade_data')),
            'huggingface': safe_json_parse(comic.get('huggingface_grade_data')),
            'local': safe_json_parse(comic.get('local_llm_grade_data')),
        },

        # Defects
        'defects': safe_json_parse(comic.get('confirmed_defects'), []),
        'allDetectedDefects': safe_json_parse(comic.get('all_detected_defects'), []),

        # Pricing
        'estimatedValue': comic.get('consensus_price'),
        'valueRange': {
            'low': comic.get('price_range_low'),
            'high': comic.get('price_range_high'),
        },
        'pricingConfidence': comic.get('pricing_confidence'),
        'marketTrend': comic.get('market_trend'),
        'pricingSources': {
            'gpa': safe_json_parse(comic.get('gpa_price_data')),
            'heritage': safe_json_parse(comic.get('heritage_price_data')),
            'ebay': safe_json_parse(comic.get('ebay_price_data')),
        },

        # Purchase/Sale info
        'buyPrice': comic.get('buy_price'),
        'buyDate': comic.get('buy_date'),
        'buySource': comic.get('buy_source'),
        'soldPrice': comic.get('sold_price'),
        'soldDate': comic.get('sold_date'),

        # Images
        'imageUrl': front_url,
        'frontImageUrl': front_url,
        'backImageUrl': back_url,

        # Metadata
        'writer': comic.get('writer'),
        'coverArtist': comic.get('cover_artist'),
        'interiorArtist': comic.get('interior_artist'),
        'characters': comic.get('characters'),
        'era': comic.get('era'),
        'genre': comic.get('genre'),
        'storyTitle': comic.get('story_title'),

        # Portal/Marketplace
        'publishedToPortal': bool(comic.get('published_to_portal')),
        'portalNotes': comic.get('portal_notes'),
        'forSale': bool(comic.get('marked_for_sale')),
        'askingPrice': comic.get('asking_price'),

        # Timestamps
        'createdAt': firestore.SERVER_TIMESTAMP,
        'updatedAt': firestore.SERVER_TIMESTAMP,
        'gradedAt': comic.get('date_added'),
        'migratedAt': datetime.utcnow().isoformat(),
    }

    # Remove None values
    doc_data = {k: v for k, v in doc_data.items() if v is not None}

    # Add to Firestore
    doc_ref = db.collection('collectibles').add(doc_data)
    return doc_ref[1].id


def main():
    print("=" * 60)
    print("EPOCGS Collection Migration to Firebase")
    print("=" * 60)

    # Initialize Firebase
    print("\n[1/4] Initializing Firebase...")
    try:
        db, bucket = init_firebase()
        print("  ✓ Firebase initialized")
    except Exception as e:
        print(f"  ✗ Firebase init failed: {e}")
        print("\n  Make sure you have a service account JSON at:")
        print(f"  {SERVICE_ACCOUNT}")
        print("\n  Or run: gcloud auth application-default login")
        return 1

    # Fetch comics from SQLite
    print("\n[2/4] Reading comics from SQLite...")
    comics = get_comics_from_sqlite()
    print(f"  ✓ Found {len(comics)} graded comics")

    # Check for existing migration
    print("\n[3/4] Checking for existing migration...")
    existing = list(db.collection('collectibles').where('source', '==', 'desktop_migration').limit(1).stream())
    if existing:
        print(f"  ! Migration already exists. Delete existing docs first or skip.")
        response = input("  Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("  Aborted.")
            return 0

    # Migrate comics
    print(f"\n[4/4] Migrating {len(comics)} comics to Firebase...")
    success = 0
    failed = 0

    for i, comic in enumerate(comics):
        title = comic.get('title', 'Unknown')
        issue = comic.get('issue_number', '')
        print(f"\n[{i+1}/{len(comics)}] {title} #{issue}")

        try:
            doc_id = migrate_comic(db, bucket, comic, COMMANDER_USER_ID)
            print(f"  ✓ Created document: {doc_id}")
            success += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"  ✓ Success: {success}")
    print(f"  ✗ Failed:  {failed}")
    print(f"  Total:     {len(comics)}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
