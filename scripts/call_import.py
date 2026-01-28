#!/usr/bin/env python3
"""Call Firebase importCollection function to migrate comics"""

import sqlite3
import json
import requests
from pathlib import Path

# Paths
SQLITE_DB = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/collectibles.db")
FUNCTION_URL = "https://us-central1-echo-prime-ai.cloudfunctions.net/importCollection"

def get_comics():
    """Fetch comics from SQLite"""
    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, issue_number, publisher, publication_year,
               consensus_grade, grade_label, grade_confidence,
               front_grade, back_grade, consensus_price,
               price_range_low, price_range_high, market_trend,
               key_issue, key_issue_reason, variant_cover, variant_description,
               confirmed_defects, date_added
        FROM comics
        WHERE consensus_grade IS NOT NULL
        ORDER BY id ASC
    """)

    comics = []
    for row in cursor.fetchall():
        comic = dict(row)

        # Parse defects
        defects = []
        if comic.get('confirmed_defects'):
            try:
                defects = json.loads(comic['confirmed_defects'])
            except:
                pass

        comics.append({
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
        })

    conn.close()
    return comics


def main():
    print("=" * 60)
    print("EPOCGS Collection Import via Firebase Function")
    print("=" * 60)

    print("\n[1/3] Reading comics from SQLite...")
    comics = get_comics()
    print(f"  Found {len(comics)} graded comics")

    # Batch in groups of 50 (Firestore batch limit is 500)
    batch_size = 50
    total_imported = 0

    for i in range(0, len(comics), batch_size):
        batch = comics[i:i + batch_size]
        print(f"\n[2/3] Importing batch {i // batch_size + 1} ({len(batch)} comics)...")

        payload = {
            "data": {
                "comics": batch,
                "adminSecret": "BMC_COMMANDER_EPOCGS_2025"
            }
        }

        try:
            response = requests.post(FUNCTION_URL, json=payload, timeout=120)
            result = response.json()

            if result.get('result', {}).get('success'):
                imported = result['result']['imported']
                total_imported += imported
                print(f"  Imported {imported} comics")
            else:
                print(f"  Error: {result}")
        except Exception as e:
            print(f"  Failed: {e}")

    print("\n" + "=" * 60)
    print("[3/3] Migration Complete!")
    print("=" * 60)
    print(f"  Total imported: {total_imported}")


if __name__ == "__main__":
    main()
