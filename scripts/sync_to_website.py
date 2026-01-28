#!/usr/bin/env python3
"""
Sync comics from SQLite to website JSON
Run this after grading new items to update the website collection
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Paths
SQLITE_DB = Path("P:/SOVEREIGN_APPS/collectibles_grading_system/collectibles.db")
WEBSITE_JSON = Path("P:/SOVEREIGN_APPS/website/data/comics.json")
WEBSITE_IMAGES = Path("P:/SOVEREIGN_APPS/website/public/comics")


def sync_comics():
    """Export all graded comics to website JSON"""
    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, issue_number, publisher, publication_year,
               consensus_grade, grade_label, grade_confidence,
               front_grade, back_grade, consensus_price,
               price_range_low, price_range_high, market_trend,
               key_issue, key_issue_reason, variant_cover, variant_description,
               front_image_path, confirmed_defects, date_added
        FROM comics
        WHERE consensus_grade IS NOT NULL
        ORDER BY date_added DESC
    """)

    comics = []
    total_value = 0

    for row in cursor.fetchall():
        comic = dict(row)

        # Parse defects JSON
        defects = []
        if comic.get('confirmed_defects'):
            try:
                defects = json.loads(comic['confirmed_defects'])
            except:
                pass

        # Calculate image URL for website
        image_url = None
        if comic.get('front_image_path'):
            img_path = Path(comic['front_image_path'])
            if img_path.exists():
                # Copy to website public folder if needed
                dest = WEBSITE_IMAGES / img_path.name
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(img_path, dest)
                image_url = f"/comics/{img_path.name}"

        # Format for website
        comics.append({
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

    conn.close()

    # Write to website JSON
    output = {
        "collectionName": "The Commander's Comic Reserve",
        "owner": "Commander Bobby Don McWilliams II",
        "totalCount": len(comics),
        "totalValue": total_value,
        "lastUpdated": datetime.now().isoformat(),
        "comics": comics
    }

    WEBSITE_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(WEBSITE_JSON, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Synced {len(comics)} comics to website")
    print(f"Total collection value: ${total_value:,.2f}")
    print(f"Output: {WEBSITE_JSON}")


if __name__ == "__main__":
    sync_comics()
