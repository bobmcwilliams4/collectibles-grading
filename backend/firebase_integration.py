"""
Firebase Firestore Integration for EPOCGS Desktop App
Dual-storage pattern: SQLite (primary, local) + Firestore (cloud sync)

Synced from: P:/SOVEREIGN_APPS/website/
Author: CLAUDE_SECONDARY
Date: 2026-01-06
"""

import os
import json
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
from loguru import logger

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage
    FIREBASE_AVAILABLE = True
except ImportError:
    logger.warning("firebase-admin not installed. Cloud sync disabled. Install: pip install firebase-admin")
    FIREBASE_AVAILABLE = False

from .types import (
    GradedItem,
    UserCollection,
    ItemType,
    ListingStatus,
    MarketResearch
)


class FirebaseIntegration:
    """
    Firebase Firestore integration for EPOCGS
    Implements dual-storage pattern: SQLite (local) + Firestore (cloud)
    """

    def __init__(self, credentials_path: Optional[str] = None, enable_sync: bool = True):
        """
        Initialize Firebase integration

        Args:
            credentials_path: Path to Firebase service account JSON
            enable_sync: Enable cloud sync (default: True, can disable for offline mode)
        """
        self.enabled = enable_sync and FIREBASE_AVAILABLE
        self.db: Optional[firestore.Client] = None
        self.storage_bucket = None

        if not self.enabled:
            logger.warning("Firebase sync is DISABLED")
            return

        # Load credentials from vault or provided path
        if credentials_path is None:
            credentials_path = self._find_credentials()

        if credentials_path and Path(credentials_path).exists():
            try:
                cred = credentials.Certificate(credentials_path)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred, {
                        'storageBucket': 'echo-prime-ai.appspot.com'
                    })
                self.db = firestore.client()
                self.storage_bucket = storage.bucket()
                logger.success(f"Firebase initialized successfully from {credentials_path}")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {e}")
                self.enabled = False
        else:
            logger.warning("Firebase credentials not found. Cloud sync disabled.")
            self.enabled = False

    def _find_credentials(self) -> Optional[str]:
        """Find Firebase credentials in vault"""
        vault_paths = [
            "O:/ECHO_OMEGA_PRIME/.promethian_vault/firebase_echo_prime_service_account.json",
            "E:/ECHO_OMEGA_PRIME/.promethian_vault/firebase_echo_prime_service_account.json",
            "P:/SOVEREIGN_APPS/collectibles_grading_system/backend/config/firebase_credentials.json"
        ]

        for path in vault_paths:
            if Path(path).exists():
                return path

        return None

    async def create_graded_item(self, item: GradedItem) -> bool:
        """
        Create graded item in Firestore

        Args:
            item: GradedItem to create

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Firestore sync disabled, skipping create")
            return False

        try:
            doc_ref = self.db.collection('graded_items').document(item.id)
            doc_ref.set(item.dict(exclude_none=True))
            logger.success(f"Created graded item in Firestore: {item.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create graded item in Firestore: {e}")
            return False

    async def update_graded_item(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update graded item in Firestore

        Args:
            item_id: Item ID to update
            updates: Fields to update

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            updates['updated_at'] = datetime.utcnow()
            doc_ref = self.db.collection('graded_items').document(item_id)
            doc_ref.update(updates)
            logger.success(f"Updated graded item in Firestore: {item_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update graded item: {e}")
            return False

    async def get_graded_item(self, item_id: str) -> Optional[GradedItem]:
        """Get graded item from Firestore"""
        if not self.enabled:
            return None

        try:
            doc = self.db.collection('graded_items').document(item_id).get()
            if doc.exists:
                return GradedItem(**doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Failed to get graded item: {e}")
            return None

    async def list_graded_items(
        self,
        owner_id: str,
        item_type: Optional[ItemType] = None,
        limit: int = 100
    ) -> List[GradedItem]:
        """
        List graded items for user

        Args:
            owner_id: User ID
            item_type: Filter by item type (optional)
            limit: Max results

        Returns:
            List of GradedItem objects
        """
        if not self.enabled:
            return []

        try:
            query = self.db.collection('graded_items') \
                .where('owner_id', '==', owner_id) \
                .order_by('created_at', direction=firestore.Query.DESCENDING) \
                .limit(limit)

            if item_type:
                query = query.where('item_type', '==', item_type.value)

            docs = query.stream()
            items = [GradedItem(**doc.to_dict()) for doc in docs]
            logger.info(f"Retrieved {len(items)} graded items from Firestore")
            return items
        except Exception as e:
            logger.error(f"Failed to list graded items: {e}")
            return []

    async def delete_graded_item(self, item_id: str) -> bool:
        """Delete graded item from Firestore"""
        if not self.enabled:
            return False

        try:
            self.db.collection('graded_items').document(item_id).delete()
            logger.success(f"Deleted graded item from Firestore: {item_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete graded item: {e}")
            return False

    async def create_collection(self, collection: UserCollection) -> bool:
        """Create user collection in Firestore"""
        if not self.enabled:
            return False

        try:
            doc_ref = self.db.collection('user_collections').document(collection.id)
            doc_ref.set(collection.dict(exclude_none=True))
            logger.success(f"Created collection in Firestore: {collection.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False

    async def update_collection(self, collection_id: str, updates: Dict[str, Any]) -> bool:
        """Update user collection in Firestore"""
        if not self.enabled:
            return False

        try:
            updates['updated_at'] = datetime.utcnow()
            doc_ref = self.db.collection('user_collections').document(collection_id)
            doc_ref.update(updates)
            logger.success(f"Updated collection in Firestore: {collection_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update collection: {e}")
            return False

    async def link_to_marketplace(self, item_id: str, listing_id: str) -> bool:
        """
        Link graded item to marketplace listing

        Args:
            item_id: Graded item ID
            listing_id: Marketplace listing ID

        Returns:
            True if successful
        """
        return await self.update_graded_item(item_id, {
            'marketplace_listing_id': listing_id,
            'listing_status': ListingStatus.LISTED.value,
            'listed_at': datetime.utcnow()
        })

    async def upload_image(self, local_path: str, remote_path: str) -> Optional[str]:
        """
        Upload image to Firebase Storage

        Args:
            local_path: Local file path
            remote_path: Remote storage path (e.g., "graded_items/item_123/front.jpg")

        Returns:
            Public URL if successful, None otherwise
        """
        if not self.enabled or not self.storage_bucket:
            return None

        try:
            blob = self.storage_bucket.blob(remote_path)
            blob.upload_from_filename(local_path)
            blob.make_public()
            url = blob.public_url
            logger.success(f"Uploaded image to Firebase Storage: {remote_path}")
            return url
        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            return None

    async def sync_from_sqlite(self, sqlite_items: List[Dict[str, Any]], owner_id: str) -> Dict[str, Any]:
        """
        Sync items from SQLite to Firestore (one-time migration or periodic sync)

        Args:
            sqlite_items: List of items from SQLite database
            owner_id: User ID

        Returns:
            Sync statistics
        """
        if not self.enabled:
            return {'success': False, 'error': 'Firebase sync disabled'}

        stats = {
            'total': len(sqlite_items),
            'created': 0,
            'updated': 0,
            'failed': 0,
            'errors': []
        }

        for item_data in sqlite_items:
            try:
                # Convert SQLite data to GradedItem
                graded_item = self._convert_sqlite_to_graded_item(item_data, owner_id)

                # Check if item exists
                existing = await self.get_graded_item(graded_item.id)

                if existing:
                    # Update if local version is newer
                    if graded_item.updated_at > existing.updated_at:
                        await self.update_graded_item(graded_item.id, graded_item.dict(exclude_none=True))
                        stats['updated'] += 1
                else:
                    # Create new item
                    await self.create_graded_item(graded_item)
                    stats['created'] += 1

            except Exception as e:
                logger.error(f"Failed to sync item: {e}")
                stats['failed'] += 1
                stats['errors'].append(str(e))

        stats['success'] = stats['failed'] == 0
        logger.info(f"Sync complete: {stats['created']} created, {stats['updated']} updated, {stats['failed']} failed")
        return stats

    def _convert_sqlite_to_graded_item(self, sqlite_data: Dict[str, Any], owner_id: str) -> GradedItem:
        """
        Convert SQLite comic data to GradedItem format

        Args:
            sqlite_data: Raw SQLite row data
            owner_id: User ID

        Returns:
            GradedItem object
        """
        # Map SQLite fields to GradedItem fields
        return GradedItem(
            id=str(sqlite_data.get('id', '')),
            owner_id=owner_id,
            item_type=ItemType.COMIC,  # Assume comics for existing data
            title=sqlite_data.get('title', 'Unknown'),
            subtitle=sqlite_data.get('issue_number'),
            publisher=sqlite_data.get('publisher'),
            publication_year=sqlite_data.get('publication_year'),
            issue_number=sqlite_data.get('issue_number'),
            variant_cover=sqlite_data.get('variant_description'),
            key_issue=sqlite_data.get('key_issue', False),
            consensus_grade=sqlite_data.get('consensus_grade', 0.0),
            grade_label=sqlite_data.get('grade_label', 'UNKNOWN'),
            grade_confidence=sqlite_data.get('confidence', 0.8),
            front_grade=sqlite_data.get('front_grade'),
            back_grade=sqlite_data.get('back_grade'),
            defects=json.loads(sqlite_data.get('defects', '[]')) if isinstance(sqlite_data.get('defects'), str) else [],
            consensus_price=sqlite_data.get('consensus_price'),
            price_range_low=sqlite_data.get('price_range_low'),
            price_range_high=sqlite_data.get('price_range_high'),
            front_image_url=sqlite_data.get('front_image_path'),
            back_image_url=sqlite_data.get('back_image_path'),
            listing_status=ListingStatus.NOT_LISTED,
            price_verified=False,
            created_at=sqlite_data.get('date_added', datetime.utcnow()),
            updated_at=datetime.utcnow(),
            last_graded=sqlite_data.get('last_graded')
        )


# Singleton instance
_firebase_instance: Optional[FirebaseIntegration] = None


def get_firebase() -> FirebaseIntegration:
    """Get or create Firebase integration singleton"""
    global _firebase_instance
    if _firebase_instance is None:
        _firebase_instance = FirebaseIntegration()
    return _firebase_instance


# Async helper functions for easy usage
async def sync_item_to_cloud(item: GradedItem) -> bool:
    """Sync graded item to cloud"""
    fb = get_firebase()
    return await fb.create_graded_item(item)


async def sync_from_local_db(sqlite_items: List[Dict[str, Any]], owner_id: str) -> Dict[str, Any]:
    """Sync all items from SQLite to Firestore"""
    fb = get_firebase()
    return await fb.sync_from_sqlite(sqlite_items, owner_id)
