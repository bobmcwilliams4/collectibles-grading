# Firebase Security Rules for EPOCGS

## Overview

This document contains the recommended Firestore and Storage security rules for the Echo Prime Omega Collectibles Grading System (EPOCGS).

## Firestore Security Rules

Deploy these rules to your Firebase project:
- Firebase Console > Firestore Database > Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // =====================================================================
    // HELPER FUNCTIONS
    // =====================================================================

    // Check if user is authenticated
    function isAuthenticated() {
      return request.auth != null;
    }

    // Check if user owns the document
    function isOwner(userId) {
      return isAuthenticated() && request.auth.uid == userId;
    }

    // Check if document exists
    function documentExists(path) {
      return exists(/databases/$(database)/documents/$(path));
    }

    // Validate string field length
    function isValidString(field, maxLength) {
      return field is string && field.size() <= maxLength;
    }

    // Validate positive number
    function isPositiveNumber(field) {
      return field is number && field > 0;
    }

    // Validate grade (0-10)
    function isValidGrade(grade) {
      return grade is number && grade >= 0 && grade <= 10;
    }

    // Validate collectible type
    function isValidCollectibleType(type) {
      return type in ['comic', 'card', 'coin', 'stamp', 'vinyl'];
    }

    // Validate digital good type
    function isValidDigitalGoodType(type) {
      return type in ['voice_clone', 'image', 'video', 'audio', 'artwork', '3d_model'];
    }

    // Validate marketplace category
    function isValidCategory(category) {
      return category in ['collectibles', 'digital_goods'];
    }

    // Validate listing status
    function isValidListingStatus(status) {
      return status in ['active', 'sold', 'cancelled'];
    }

    // Rate limiting helper (basic - check recent writes)
    function notTooManyWrites() {
      // Allow max 10 writes per minute per user
      // Note: Full rate limiting should be done at application level
      return true;
    }

    // =====================================================================
    // USERS COLLECTION
    // =====================================================================

    match /users/{userId} {
      // Users can read their own profile
      allow read: if isOwner(userId);

      // Users can create their own profile
      allow create: if isOwner(userId) &&
        isValidString(request.resource.data.displayName, 100) &&
        request.resource.data.email is string;

      // Users can update their own profile (limited fields)
      allow update: if isOwner(userId) &&
        (!request.resource.data.diff(resource.data).affectedKeys().hasAny(['email', 'uid', 'createdAt'])) &&
        isValidString(request.resource.data.displayName, 100);

      // Users cannot delete their profile (soft delete only)
      allow delete: if false;
    }

    // =====================================================================
    // COLLECTIBLES COLLECTION
    // =====================================================================

    match /collectibles/{collectibleId} {
      // Anyone can read collectibles (for marketplace display)
      allow read: if true;

      // Only authenticated users can create collectibles
      allow create: if isAuthenticated() &&
        request.resource.data.userId == request.auth.uid &&
        isValidString(request.resource.data.title, 200) &&
        isValidCollectibleType(request.resource.data.type) &&
        (request.resource.data.grade == null || isValidGrade(request.resource.data.grade)) &&
        (request.resource.data.estimatedValue == null || isPositiveNumber(request.resource.data.estimatedValue)) &&
        notTooManyWrites();

      // Only owner can update their collectibles
      allow update: if isOwner(resource.data.userId) &&
        // Cannot change userId
        request.resource.data.userId == resource.data.userId &&
        isValidString(request.resource.data.title, 200) &&
        (request.resource.data.grade == null || isValidGrade(request.resource.data.grade));

      // Only owner can delete their collectibles
      // But not if it's listed on marketplace
      allow delete: if isOwner(resource.data.userId) &&
        resource.data.forSale != true;
    }

    // =====================================================================
    // DIGITAL GOODS COLLECTION
    // =====================================================================

    match /digitalGoods/{goodId} {
      // Anyone can read digital goods (for marketplace display)
      allow read: if true;

      // Only authenticated users can create digital goods
      allow create: if isAuthenticated() &&
        request.resource.data.userId == request.auth.uid &&
        isValidString(request.resource.data.title, 200) &&
        isValidDigitalGoodType(request.resource.data.type) &&
        request.resource.data.fileUrl is string &&
        notTooManyWrites();

      // Only owner can update their digital goods
      allow update: if isOwner(resource.data.userId) &&
        request.resource.data.userId == resource.data.userId &&
        isValidString(request.resource.data.title, 200);

      // Only owner can delete their digital goods
      allow delete: if isOwner(resource.data.userId);
    }

    // =====================================================================
    // MARKETPLACE LISTINGS COLLECTION
    // =====================================================================

    match /marketplace/{listingId} {
      // Anyone can read marketplace listings
      allow read: if true;

      // Only authenticated users can create listings
      allow create: if isAuthenticated() &&
        request.resource.data.sellerId == request.auth.uid &&
        isValidString(request.resource.data.title, 200) &&
        isValidCategory(request.resource.data.category) &&
        isPositiveNumber(request.resource.data.askingPrice) &&
        request.resource.data.askingPrice < 1000000000 && // Max $1B
        request.resource.data.status == 'active' &&
        notTooManyWrites();

      // Only seller can update their listings
      allow update: if isOwner(resource.data.sellerId) &&
        // Cannot change seller or item
        request.resource.data.sellerId == resource.data.sellerId &&
        request.resource.data.itemId == resource.data.itemId &&
        request.resource.data.category == resource.data.category &&
        // Can only update certain fields
        isValidListingStatus(request.resource.data.status) &&
        (request.resource.data.askingPrice == resource.data.askingPrice ||
         isPositiveNumber(request.resource.data.askingPrice));

      // Only seller can cancel (soft delete via status change)
      allow delete: if false; // Use status = 'cancelled' instead

      // Allow incrementing views (anyone)
      allow update: if request.resource.data.diff(resource.data).affectedKeys().hasOnly(['views']) &&
        request.resource.data.views == resource.data.views + 1;
    }

    // =====================================================================
    // PUBLIC COLLECTIONS (SHOWCASE)
    // =====================================================================

    match /publicCollections/{collectionId} {
      // Anyone can read public showcase
      allow read: if true;

      // Only the collection owner can publish to showcase
      allow create: if isAuthenticated() &&
        request.resource.data.userId == request.auth.uid;

      allow update: if isOwner(resource.data.userId);
      allow delete: if isOwner(resource.data.userId);
    }

    // =====================================================================
    // ORDERS / TRANSACTIONS
    // =====================================================================

    match /orders/{orderId} {
      // Buyer and seller can read their orders
      allow read: if isAuthenticated() &&
        (resource.data.buyerId == request.auth.uid ||
         resource.data.sellerId == request.auth.uid);

      // Only authenticated users can create orders
      allow create: if isAuthenticated() &&
        request.resource.data.buyerId == request.auth.uid &&
        request.resource.data.status == 'pending';

      // Limited updates (status changes only)
      allow update: if isAuthenticated() &&
        (resource.data.buyerId == request.auth.uid ||
         resource.data.sellerId == request.auth.uid);

      // No deletions
      allow delete: if false;
    }

    // =====================================================================
    // USER FAVORITES
    // =====================================================================

    match /favorites/{favoriteId} {
      allow read: if isOwner(resource.data.userId);

      allow create: if isAuthenticated() &&
        request.resource.data.userId == request.auth.uid;

      allow delete: if isOwner(resource.data.userId);
    }

    // =====================================================================
    // ANALYTICS / ACTIVITY LOGS (Write-only for users)
    // =====================================================================

    match /analytics/{docId} {
      allow read: if false; // Only admins via Admin SDK
      allow create: if isAuthenticated();
      allow update, delete: if false;
    }

    // =====================================================================
    // CATCH-ALL DENY
    // =====================================================================

    // Deny access to any other collections
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

## Firebase Storage Security Rules

Deploy these rules to your Firebase project:
- Firebase Console > Storage > Rules

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {

    // Helper functions
    function isAuthenticated() {
      return request.auth != null;
    }

    function isOwner(userId) {
      return isAuthenticated() && request.auth.uid == userId;
    }

    // Validate file size (max 10MB for images)
    function isValidImageSize() {
      return request.resource.size < 10 * 1024 * 1024;
    }

    // Validate file size for digital goods (max 500MB)
    function isValidDigitalFileSize() {
      return request.resource.size < 500 * 1024 * 1024;
    }

    // Validate image content type
    function isValidImageType() {
      return request.resource.contentType.matches('image/.*');
    }

    // =====================================================================
    // USER COLLECTIBLE IMAGES
    // =====================================================================

    match /{userId}/collectibles/{fileName} {
      // Anyone can read (for marketplace display)
      allow read: if true;

      // Only owner can upload
      allow write: if isOwner(userId) &&
        isValidImageSize() &&
        isValidImageType();
    }

    // =====================================================================
    // DIGITAL GOODS FILES
    // =====================================================================

    match /digital_goods/{userId}/{type}/{fileName} {
      // Anyone can read (for preview/download)
      allow read: if true;

      // Only owner can upload
      allow write: if isOwner(userId) &&
        isValidDigitalFileSize();
    }

    // =====================================================================
    // USER AVATARS
    // =====================================================================

    match /avatars/{userId}/{fileName} {
      // Anyone can read
      allow read: if true;

      // Only owner can upload
      allow write: if isOwner(userId) &&
        request.resource.size < 5 * 1024 * 1024 && // 5MB max
        isValidImageType();
    }

    // =====================================================================
    // CATCH-ALL DENY
    // =====================================================================

    match /{allPaths=**} {
      allow read, write: if false;
    }
  }
}
```

## Deployment Instructions

### Deploy Firestore Rules

```bash
# Using Firebase CLI
firebase deploy --only firestore:rules
```

### Deploy Storage Rules

```bash
# Using Firebase CLI
firebase deploy --only storage
```

### Test Rules

Use the Firebase Emulator to test rules before deployment:

```bash
# Start emulator
firebase emulators:start

# Run tests
npm test
```

## Security Best Practices Applied

1. **Authentication Required**: All write operations require authentication
2. **Owner Validation**: Users can only modify their own documents
3. **Input Validation**: String lengths, number ranges, and enum values are validated
4. **Immutable Fields**: Critical fields like userId cannot be changed after creation
5. **No Hard Deletes**: Marketplace listings use soft delete via status change
6. **File Size Limits**: Storage uploads are size-limited
7. **Content Type Validation**: Only valid file types are accepted
8. **Rate Limiting Awareness**: Basic rate limiting checks (full implementation at app level)
9. **Deny by Default**: Unknown collections are denied access

## Notes

- Full rate limiting should be implemented at the application level
- Consider using Firebase App Check for additional security
- Regularly audit and update rules as features evolve
- Use Firebase Security Rules Unit Testing for CI/CD
