// Firebase Configuration - Environment Variables REQUIRED
// Project: echo-prime-ai
// See .env.example for required environment variables

import { initializeApp, getApps, FirebaseApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  User,
  browserLocalPersistence,
  setPersistence
} from 'firebase/auth';
import {
  getFirestore,
  collection,
  doc,
  getDocs,
  getDoc,
  addDoc,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  limit,
  startAfter,
  Timestamp,
  onSnapshot,
  enableIndexedDbPersistence,
  DocumentSnapshot,
  QueryDocumentSnapshot,
  FirestoreError,
  writeBatch,
  increment,
  DocumentData
} from 'firebase/firestore';
import { getStorage, ref, uploadBytes, getDownloadURL, uploadBytesResumable, UploadTask } from 'firebase/storage';

// ============================================================================
// ENVIRONMENT VARIABLE VALIDATION
// ============================================================================

interface FirebaseEnvConfig {
  apiKey: string;
  authDomain: string;
  projectId: string;
  storageBucket: string;
  messagingSenderId: string;
  appId: string;
  databaseURL?: string;
  measurementId?: string;
}

function validateFirebaseEnv(): FirebaseEnvConfig {
  const requiredVars = [
    'NEXT_PUBLIC_FIREBASE_API_KEY',
    'NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN',
    'NEXT_PUBLIC_FIREBASE_PROJECT_ID',
    'NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET',
    'NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID',
    'NEXT_PUBLIC_FIREBASE_APP_ID'
  ] as const;

  const missingVars: string[] = [];

  for (const varName of requiredVars) {
    if (!process.env[varName]) {
      missingVars.push(varName);
    }
  }

  if (missingVars.length > 0) {
    const errorMsg = `Missing required Firebase environment variables:\n${missingVars.join('\n')}\n\nPlease check your .env.local file. See .env.example for required variables.`;
    console.error(errorMsg);
    throw new Error(errorMsg);
  }

  return {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY!,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || 'echo-prime-ai.firebaseapp.com',
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID!,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || 'echo-prime-ai.firebasestorage.app',
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID!,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID!,
    databaseURL: process.env.NEXT_PUBLIC_FIREBASE_DATABASE_URL,
    measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID
  };
}

// ============================================================================
// FIREBASE INITIALIZATION
// ============================================================================

let app: FirebaseApp;
let firestorePersistenceEnabled = false;

try {
  const firebaseConfig = validateFirebaseEnv();
  app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
} catch (error) {
  console.error('Firebase initialization failed:', error);
  throw error;
}

export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);

// Enable offline persistence (client-side only)
if (typeof window !== 'undefined' && !firestorePersistenceEnabled) {
  enableIndexedDbPersistence(db)
    .then(() => {
      firestorePersistenceEnabled = true;
      console.log('Firestore offline persistence enabled');
    })
    .catch((err) => {
      if (err.code === 'failed-precondition') {
        console.warn('Firestore persistence failed: Multiple tabs open');
      } else if (err.code === 'unimplemented') {
        console.warn('Firestore persistence not available in this browser');
      }
    });
}

// ============================================================================
// ERROR HANDLING UTILITIES
// ============================================================================

export class FirebaseOperationError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly originalError?: unknown
  ) {
    super(message);
    this.name = 'FirebaseOperationError';
  }
}

function handleFirestoreError(error: unknown, operation: string): never {
  const firestoreError = error as FirestoreError;
  const errorCode = firestoreError?.code || 'unknown';
  const errorMessage = firestoreError?.message || 'Unknown error occurred';

  const userFriendlyMessages: Record<string, string> = {
    'permission-denied': 'You do not have permission to perform this action.',
    'not-found': 'The requested document was not found.',
    'already-exists': 'This item already exists.',
    'resource-exhausted': 'Too many requests. Please try again later.',
    'failed-precondition': 'Operation failed due to a conflict.',
    'aborted': 'Operation was aborted. Please try again.',
    'unavailable': 'Service temporarily unavailable. Please try again.',
    'unauthenticated': 'Please sign in to continue.',
    'invalid-argument': 'Invalid data provided.',
    'deadline-exceeded': 'Request timed out. Please try again.'
  };

  const friendlyMessage = userFriendlyMessages[errorCode] || `${operation} failed: ${errorMessage}`;

  console.error(`Firebase ${operation} error:`, { code: errorCode, message: errorMessage, error });
  throw new FirebaseOperationError(friendlyMessage, errorCode, error);
}

// Rate limiting tracker
const rateLimitTracker = {
  operations: new Map<string, { count: number; resetTime: number }>(),
  maxOperationsPerMinute: 60,

  checkLimit(operationType: string): boolean {
    const now = Date.now();
    const tracker = this.operations.get(operationType);

    if (!tracker || now > tracker.resetTime) {
      this.operations.set(operationType, { count: 1, resetTime: now + 60000 });
      return true;
    }

    if (tracker.count >= this.maxOperationsPerMinute) {
      console.warn(`Rate limit approaching for ${operationType}`);
      return false;
    }

    tracker.count++;
    return true;
  }
};

// ============================================================================
// AUTH HELPERS
// ============================================================================

export const googleProvider = new GoogleAuthProvider();
googleProvider.addScope('email');
googleProvider.addScope('profile');

export const signInWithGoogle = async (): Promise<User> => {
  try {
    await setPersistence(auth, browserLocalPersistence);
    const result = await signInWithPopup(auth, googleProvider);
    return result.user;
  } catch (error) {
    handleFirestoreError(error, 'Sign in');
  }
};

export const signOut = async (): Promise<void> => {
  try {
    await firebaseSignOut(auth);
  } catch (error) {
    handleFirestoreError(error, 'Sign out');
  }
};

export const onAuthChange = (callback: (user: User | null) => void): (() => void) => {
  return onAuthStateChanged(auth, callback);
};

export const getCurrentUser = (): User | null => {
  return auth.currentUser;
};

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export type CollectibleType = 'comic' | 'card' | 'coin' | 'stamp' | 'vinyl';
export type DigitalGoodType = 'voice_clone' | 'image' | 'video' | 'audio' | 'artwork' | '3d_model';
export type MarketplaceCategory = 'collectibles' | 'digital_goods';

export interface Collectible {
  id: string;
  userId: string;
  type: CollectibleType;
  title: string;
  description?: string;
  grade?: number;
  estimatedValue?: number;
  imageUrl?: string;
  thumbnailUrl?: string;
  analysis?: CollectibleAnalysis;
  forSale?: boolean;
  askingPrice?: number;
  createdAt: Timestamp;
  updatedAt?: Timestamp;
}

export interface CollectibleAnalysis {
  overallGrade: number;
  confidence: number;
  models: string[];
  factors: {
    name: string;
    score: number;
    notes: string;
  }[];
  timestamp: string;
}

export interface DigitalGood {
  id: string;
  userId: string;
  type: DigitalGoodType;
  title: string;
  description?: string;
  fileUrl: string;
  previewUrl?: string;
  thumbnailUrl?: string;
  fileSize?: number;
  format?: string;
  duration?: number;
  license?: 'personal' | 'commercial' | 'exclusive';
  tags?: string[];
  createdAt: Timestamp;
  updatedAt?: Timestamp;
}

export interface MarketplaceListing {
  id: string;
  category: MarketplaceCategory;
  itemId: string;
  sellerId: string;
  sellerName: string;
  sellerAvatar?: string;
  title: string;
  type: CollectibleType | DigitalGoodType;
  grade?: number;
  license?: string;
  askingPrice: number;
  imageUrl?: string;
  previewUrl?: string;
  description?: string;
  tags?: string[];
  status: 'active' | 'sold' | 'cancelled';
  views?: number;
  favorites?: number;
  acceptsOffers?: boolean;
  minimumOffer?: number;
  createdAt: Timestamp;
}

export interface PaginatedResult<T> {
  items: T[];
  lastDoc: DocumentSnapshot | null;
  hasMore: boolean;
}

// ============================================================================
// INPUT VALIDATION & SANITIZATION
// ============================================================================

const TITLE_MAX_LENGTH = 200;
const DESCRIPTION_MAX_LENGTH = 5000;
const TAG_MAX_LENGTH = 50;
const MAX_TAGS = 20;

function sanitizeString(input: string, maxLength: number): string {
  if (!input || typeof input !== 'string') return '';

  // Remove potentially dangerous HTML/script content
  let sanitized = input
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<[^>]*>/g, '')
    .replace(/javascript:/gi, '')
    .replace(/on\w+\s*=/gi, '')
    .trim();

  // Truncate to max length
  if (sanitized.length > maxLength) {
    sanitized = sanitized.substring(0, maxLength);
  }

  return sanitized;
}

function validatePrice(price: number): boolean {
  return typeof price === 'number' && !isNaN(price) && price > 0 && price < 1000000000;
}

function validateGrade(grade: number): boolean {
  return typeof grade === 'number' && !isNaN(grade) && grade >= 0 && grade <= 10;
}

function sanitizeTags(tags: string[]): string[] {
  if (!Array.isArray(tags)) return [];

  return tags
    .slice(0, MAX_TAGS)
    .map(tag => sanitizeString(tag.toLowerCase(), TAG_MAX_LENGTH))
    .filter(tag => tag.length > 0);
}

// ============================================================================
// CACHING LAYER
// ============================================================================

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

class SimpleCache {
  private cache = new Map<string, CacheEntry<unknown>>();
  private defaultTTL = 60000; // 1 minute

  set<T>(key: string, data: T, ttl?: number): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: ttl || this.defaultTTL
    });
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key) as CacheEntry<T> | undefined;
    if (!entry) return null;

    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  invalidate(keyPattern: string): void {
    const keys = Array.from(this.cache.keys());
    for (const key of keys) {
      if (key.includes(keyPattern)) {
        this.cache.delete(key);
      }
    }
  }

  clear(): void {
    this.cache.clear();
  }
}

export const cache = new SimpleCache();

// ============================================================================
// COLLECTIBLE OPERATIONS
// ============================================================================

export const getUserCollectibles = async (
  userId: string,
  pageSize: number = 50,
  lastDocument?: DocumentSnapshot
): Promise<PaginatedResult<Collectible>> => {
  if (!userId || typeof userId !== 'string') {
    throw new FirebaseOperationError('Invalid user ID', 'invalid-argument');
  }

  const cacheKey = `collectibles_${userId}_${lastDocument?.id || 'first'}`;
  const cached = cache.get<PaginatedResult<Collectible>>(cacheKey);
  if (cached && !lastDocument) return cached;

  try {
    let q = query(
      collection(db, 'collectibles'),
      where('userId', '==', userId),
      orderBy('createdAt', 'desc'),
      limit(pageSize + 1) // Fetch one extra to check if there are more
    );

    if (lastDocument) {
      q = query(q, startAfter(lastDocument));
    }

    const snapshot = await getDocs(q);
    const docs = snapshot.docs;
    const hasMore = docs.length > pageSize;
    const items = docs.slice(0, pageSize).map(doc => ({
      id: doc.id,
      ...doc.data()
    } as Collectible));

    const result: PaginatedResult<Collectible> = {
      items,
      lastDoc: items.length > 0 ? docs[items.length - 1] : null,
      hasMore
    };

    if (!lastDocument) {
      cache.set(cacheKey, result);
    }

    return result;
  } catch (error) {
    handleFirestoreError(error, 'Loading collectibles');
  }
};

export const addCollectible = async (
  collectible: Omit<Collectible, 'id' | 'createdAt'>
): Promise<string> => {
  if (!rateLimitTracker.checkLimit('addCollectible')) {
    throw new FirebaseOperationError('Too many requests. Please wait.', 'resource-exhausted');
  }

  // Validate and sanitize input
  const sanitizedData = {
    ...collectible,
    title: sanitizeString(collectible.title, TITLE_MAX_LENGTH),
    description: collectible.description
      ? sanitizeString(collectible.description, DESCRIPTION_MAX_LENGTH)
      : undefined,
    createdAt: Timestamp.now()
  };

  if (!sanitizedData.title) {
    throw new FirebaseOperationError('Title is required', 'invalid-argument');
  }

  if (sanitizedData.grade !== undefined && !validateGrade(sanitizedData.grade)) {
    throw new FirebaseOperationError('Invalid grade value', 'invalid-argument');
  }

  try {
    const docRef = await addDoc(collection(db, 'collectibles'), sanitizedData);
    cache.invalidate(`collectibles_${collectible.userId}`);
    return docRef.id;
  } catch (error) {
    handleFirestoreError(error, 'Adding collectible');
  }
};

export const updateCollectible = async (
  id: string,
  updates: Partial<Collectible>
): Promise<void> => {
  if (!id || typeof id !== 'string') {
    throw new FirebaseOperationError('Invalid collectible ID', 'invalid-argument');
  }

  // Sanitize updates
  const sanitizedUpdates: Partial<Collectible> = {
    ...updates,
    updatedAt: Timestamp.now()
  };

  if (updates.title) {
    sanitizedUpdates.title = sanitizeString(updates.title, TITLE_MAX_LENGTH);
  }
  if (updates.description) {
    sanitizedUpdates.description = sanitizeString(updates.description, DESCRIPTION_MAX_LENGTH);
  }
  if (updates.grade !== undefined && !validateGrade(updates.grade)) {
    throw new FirebaseOperationError('Invalid grade value', 'invalid-argument');
  }

  try {
    await updateDoc(doc(db, 'collectibles', id), sanitizedUpdates as DocumentData);
    cache.invalidate('collectibles_');
  } catch (error) {
    handleFirestoreError(error, 'Updating collectible');
  }
};

export const deleteCollectible = async (id: string): Promise<void> => {
  if (!id || typeof id !== 'string') {
    throw new FirebaseOperationError('Invalid collectible ID', 'invalid-argument');
  }

  try {
    await deleteDoc(doc(db, 'collectibles', id));
    cache.invalidate('collectibles_');
  } catch (error) {
    handleFirestoreError(error, 'Deleting collectible');
  }
};

// ============================================================================
// MARKETPLACE OPERATIONS WITH REAL-TIME SUPPORT
// ============================================================================

export const getMarketplaceListings = async (
  category?: MarketplaceCategory,
  type?: CollectibleType | DigitalGoodType,
  pageSize: number = 50,
  lastDocument?: DocumentSnapshot
): Promise<PaginatedResult<MarketplaceListing>> => {
  const cacheKey = `marketplace_${category || 'all'}_${type || 'all'}_${lastDocument?.id || 'first'}`;
  const cached = cache.get<PaginatedResult<MarketplaceListing>>(cacheKey);
  if (cached && !lastDocument) return cached;

  try {
    let constraints: any[] = [
      where('status', '==', 'active'),
      orderBy('createdAt', 'desc'),
      limit(pageSize + 1)
    ];

    if (category) {
      constraints.push(where('category', '==', category));
    }
    if (type) {
      constraints.push(where('type', '==', type));
    }
    if (lastDocument) {
      constraints.push(startAfter(lastDocument));
    }

    const q = query(collection(db, 'marketplace'), ...constraints);
    const snapshot = await getDocs(q);

    const docs = snapshot.docs;
    const hasMore = docs.length > pageSize;
    const items = docs.slice(0, pageSize).map(doc => ({
      id: doc.id,
      ...doc.data()
    } as MarketplaceListing));

    const result: PaginatedResult<MarketplaceListing> = {
      items,
      lastDoc: items.length > 0 ? docs[items.length - 1] : null,
      hasMore
    };

    if (!lastDocument) {
      cache.set(cacheKey, result, 30000); // 30 second cache for marketplace
    }

    return result;
  } catch (error) {
    handleFirestoreError(error, 'Loading marketplace');
  }
};

// Real-time listener for marketplace updates
export const subscribeToMarketplace = (
  callback: (listings: MarketplaceListing[]) => void,
  category?: MarketplaceCategory,
  type?: CollectibleType | DigitalGoodType,
  limitCount: number = 50
): (() => void) => {
  let constraints: any[] = [
    where('status', '==', 'active'),
    orderBy('createdAt', 'desc'),
    limit(limitCount)
  ];

  if (category) {
    constraints.push(where('category', '==', category));
  }
  if (type) {
    constraints.push(where('type', '==', type));
  }

  const q = query(collection(db, 'marketplace'), ...constraints);

  return onSnapshot(
    q,
    (snapshot) => {
      const listings = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      } as MarketplaceListing));
      callback(listings);
    },
    (error) => {
      console.error('Marketplace subscription error:', error);
    }
  );
};

export const createListing = async (
  listing: Omit<MarketplaceListing, 'id' | 'createdAt' | 'status' | 'views' | 'favorites'>
): Promise<string> => {
  if (!rateLimitTracker.checkLimit('createListing')) {
    throw new FirebaseOperationError('Too many requests. Please wait.', 'resource-exhausted');
  }

  // Validate and sanitize
  if (!validatePrice(listing.askingPrice)) {
    throw new FirebaseOperationError('Invalid asking price', 'invalid-argument');
  }

  const sanitizedListing = {
    ...listing,
    title: sanitizeString(listing.title, TITLE_MAX_LENGTH),
    description: listing.description
      ? sanitizeString(listing.description, DESCRIPTION_MAX_LENGTH)
      : undefined,
    sellerName: sanitizeString(listing.sellerName, 100),
    tags: listing.tags ? sanitizeTags(listing.tags) : undefined,
    status: 'active' as const,
    views: 0,
    favorites: 0,
    createdAt: Timestamp.now()
  };

  if (!sanitizedListing.title) {
    throw new FirebaseOperationError('Title is required', 'invalid-argument');
  }

  try {
    const docRef = await addDoc(collection(db, 'marketplace'), sanitizedListing);
    cache.invalidate('marketplace_');
    return docRef.id;
  } catch (error) {
    handleFirestoreError(error, 'Creating listing');
  }
};

export const updateListingStatus = async (
  listingId: string,
  status: 'active' | 'sold' | 'cancelled'
): Promise<void> => {
  try {
    await updateDoc(doc(db, 'marketplace', listingId), {
      status,
      updatedAt: Timestamp.now()
    });
    cache.invalidate('marketplace_');
  } catch (error) {
    handleFirestoreError(error, 'Updating listing status');
  }
};

export const incrementListingViews = async (listingId: string): Promise<void> => {
  try {
    await updateDoc(doc(db, 'marketplace', listingId), {
      views: increment(1)
    });
  } catch (error) {
    // Silently fail for view tracking
    console.error('Failed to increment views:', error);
  }
};

// ============================================================================
// SEARCH FUNCTIONALITY
// ============================================================================

export interface SearchOptions {
  query: string;
  category?: MarketplaceCategory;
  type?: CollectibleType | DigitalGoodType;
  minPrice?: number;
  maxPrice?: number;
  minGrade?: number;
  pageSize?: number;
}

export const searchMarketplace = async (
  options: SearchOptions
): Promise<MarketplaceListing[]> => {
  const { query: searchQuery, category, type, minPrice, maxPrice, minGrade, pageSize = 50 } = options;

  // For now, fetch and filter client-side
  // In production, use Algolia or Firebase Extensions for full-text search
  try {
    const result = await getMarketplaceListings(category, type, 200);

    return result.items.filter(listing => {
      const matchesQuery = !searchQuery ||
        listing.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        listing.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        listing.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesPrice =
        (!minPrice || listing.askingPrice >= minPrice) &&
        (!maxPrice || listing.askingPrice <= maxPrice);

      const matchesGrade = !minGrade || (listing.grade && listing.grade >= minGrade);

      return matchesQuery && matchesPrice && matchesGrade;
    }).slice(0, pageSize);
  } catch (error) {
    handleFirestoreError(error, 'Searching marketplace');
  }
};

// ============================================================================
// DIGITAL GOODS OPERATIONS
// ============================================================================

export const getUserDigitalGoods = async (
  userId: string,
  pageSize: number = 50,
  lastDocument?: DocumentSnapshot
): Promise<PaginatedResult<DigitalGood>> => {
  if (!userId || typeof userId !== 'string') {
    throw new FirebaseOperationError('Invalid user ID', 'invalid-argument');
  }

  try {
    let q = query(
      collection(db, 'digitalGoods'),
      where('userId', '==', userId),
      orderBy('createdAt', 'desc'),
      limit(pageSize + 1)
    );

    if (lastDocument) {
      q = query(q, startAfter(lastDocument));
    }

    const snapshot = await getDocs(q);
    const docs = snapshot.docs;
    const hasMore = docs.length > pageSize;
    const items = docs.slice(0, pageSize).map(doc => ({
      id: doc.id,
      ...doc.data()
    } as DigitalGood));

    return {
      items,
      lastDoc: items.length > 0 ? docs[items.length - 1] : null,
      hasMore
    };
  } catch (error) {
    handleFirestoreError(error, 'Loading digital goods');
  }
};

export const addDigitalGood = async (
  digitalGood: Omit<DigitalGood, 'id' | 'createdAt'>
): Promise<string> => {
  if (!rateLimitTracker.checkLimit('addDigitalGood')) {
    throw new FirebaseOperationError('Too many requests. Please wait.', 'resource-exhausted');
  }

  const sanitizedData = {
    ...digitalGood,
    title: sanitizeString(digitalGood.title, TITLE_MAX_LENGTH),
    description: digitalGood.description
      ? sanitizeString(digitalGood.description, DESCRIPTION_MAX_LENGTH)
      : undefined,
    tags: digitalGood.tags ? sanitizeTags(digitalGood.tags) : undefined,
    createdAt: Timestamp.now()
  };

  if (!sanitizedData.title) {
    throw new FirebaseOperationError('Title is required', 'invalid-argument');
  }

  try {
    const docRef = await addDoc(collection(db, 'digitalGoods'), sanitizedData);
    return docRef.id;
  } catch (error) {
    handleFirestoreError(error, 'Adding digital good');
  }
};

// ============================================================================
// IMAGE UPLOAD WITH OPTIMIZATION
// ============================================================================

const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

export interface UploadProgress {
  bytesTransferred: number;
  totalBytes: number;
  percentage: number;
}

export const uploadCollectibleImage = async (
  userId: string,
  file: File,
  onProgress?: (progress: UploadProgress) => void
): Promise<{ imageUrl: string; thumbnailUrl?: string }> => {
  // Validate file
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    throw new FirebaseOperationError(
      'Invalid file type. Allowed: JPEG, PNG, WebP, GIF',
      'invalid-argument'
    );
  }

  if (file.size > MAX_IMAGE_SIZE) {
    throw new FirebaseOperationError(
      'File too large. Maximum size is 10MB',
      'invalid-argument'
    );
  }

  const timestamp = Date.now();
  const sanitizedName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
  const fileName = `${userId}/collectibles/${timestamp}_${sanitizedName}`;
  const fileRef = ref(storage, fileName);

  try {
    const uploadTask = uploadBytesResumable(fileRef, file);

    return new Promise((resolve, reject) => {
      uploadTask.on(
        'state_changed',
        (snapshot) => {
          if (onProgress) {
            onProgress({
              bytesTransferred: snapshot.bytesTransferred,
              totalBytes: snapshot.totalBytes,
              percentage: (snapshot.bytesTransferred / snapshot.totalBytes) * 100
            });
          }
        },
        (error) => {
          reject(new FirebaseOperationError('Upload failed', 'unknown', error));
        },
        async () => {
          const imageUrl = await getDownloadURL(uploadTask.snapshot.ref);
          resolve({ imageUrl });
        }
      );
    });
  } catch (error) {
    handleFirestoreError(error, 'Uploading image');
  }
};

export const uploadDigitalFile = async (
  userId: string,
  file: File,
  type: DigitalGoodType,
  onProgress?: (progress: UploadProgress) => void
): Promise<{ fileUrl: string; thumbnailUrl?: string }> => {
  const MAX_DIGITAL_SIZE = 500 * 1024 * 1024; // 500MB

  if (file.size > MAX_DIGITAL_SIZE) {
    throw new FirebaseOperationError(
      'File too large. Maximum size is 500MB',
      'invalid-argument'
    );
  }

  const timestamp = Date.now();
  const sanitizedName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
  const fileName = `${userId}/${type}/${timestamp}_${sanitizedName}`;
  const fileRef = ref(storage, `digital_goods/${fileName}`);

  try {
    const uploadTask = uploadBytesResumable(fileRef, file);

    return new Promise((resolve, reject) => {
      uploadTask.on(
        'state_changed',
        (snapshot) => {
          if (onProgress) {
            onProgress({
              bytesTransferred: snapshot.bytesTransferred,
              totalBytes: snapshot.totalBytes,
              percentage: (snapshot.bytesTransferred / snapshot.totalBytes) * 100
            });
          }
        },
        (error) => {
          reject(new FirebaseOperationError('Upload failed', 'unknown', error));
        },
        async () => {
          const fileUrl = await getDownloadURL(uploadTask.snapshot.ref);
          resolve({ fileUrl });
        }
      );
    });
  } catch (error) {
    handleFirestoreError(error, 'Uploading digital file');
  }
};

// ============================================================================
// SHOWCASE OPERATIONS
// ============================================================================

export const getPublicShowcase = async (
  limitCount: number = 20
): Promise<PaginatedResult<any>> => {
  const cacheKey = `showcase_${limitCount}`;
  const cached = cache.get<PaginatedResult<any>>(cacheKey);
  if (cached) return cached;

  try {
    const q = query(
      collection(db, 'publicCollections'),
      orderBy('totalValue', 'desc'),
      limit(limitCount)
    );
    const snapshot = await getDocs(q);

    const result: PaginatedResult<any> = {
      items: snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })),
      lastDoc: snapshot.docs[snapshot.docs.length - 1] || null,
      hasMore: false
    };

    cache.set(cacheKey, result, 120000); // 2 minute cache for showcase
    return result;
  } catch (error) {
    handleFirestoreError(error, 'Loading showcase');
  }
};

// ============================================================================
// LISTING HELPERS
// ============================================================================

export const isCollectibleListed = async (collectibleId: string): Promise<boolean> => {
  const cacheKey = `listed_${collectibleId}`;
  const cached = cache.get<boolean>(cacheKey);
  if (cached !== null) return cached;

  try {
    const q = query(
      collection(db, 'marketplace'),
      where('itemId', '==', collectibleId),
      where('category', '==', 'collectibles'),
      where('status', '==', 'active'),
      limit(1)
    );
    const snapshot = await getDocs(q);
    const isListed = !snapshot.empty;
    cache.set(cacheKey, isListed, 60000);
    return isListed;
  } catch (error) {
    handleFirestoreError(error, 'Checking listing status');
  }
};

export const getListableCollectibles = async (userId: string): Promise<Collectible[]> => {
  try {
    const result = await getUserCollectibles(userId, 200);
    const gradedCollectibles = result.items.filter(c => c.grade !== undefined && c.grade > 0);

    // Check which ones are already listed (batch check for efficiency)
    const listableCollectibles: Collectible[] = [];
    for (const collectible of gradedCollectibles) {
      const isListed = await isCollectibleListed(collectible.id);
      if (!isListed) {
        listableCollectibles.push(collectible);
      }
    }

    return listableCollectibles;
  } catch (error) {
    handleFirestoreError(error, 'Getting listable collectibles');
  }
};

export const createCollectibleListing = async (
  collectible: Collectible,
  askingPrice: number,
  user: { uid: string; displayName?: string | null; photoURL?: string | null },
  options?: { acceptsOffers?: boolean; minimumOffer?: number }
): Promise<string> => {
  if (!collectible.grade || collectible.grade <= 0) {
    throw new FirebaseOperationError('Only graded collectibles can be listed', 'invalid-argument');
  }

  if (!validatePrice(askingPrice)) {
    throw new FirebaseOperationError('Invalid asking price', 'invalid-argument');
  }

  const alreadyListed = await isCollectibleListed(collectible.id);
  if (alreadyListed) {
    throw new FirebaseOperationError('This collectible is already listed on the marketplace', 'already-exists');
  }

  try {
    // Use batch write for atomic operation
    const batch = writeBatch(db);

    // Create listing
    const listingRef = doc(collection(db, 'marketplace'));
    batch.set(listingRef, {
      category: 'collectibles',
      itemId: collectible.id,
      sellerId: user.uid,
      sellerName: sanitizeString(user.displayName || 'Anonymous', 100),
      sellerAvatar: user.photoURL || undefined,
      title: sanitizeString(collectible.title, TITLE_MAX_LENGTH),
      type: collectible.type,
      grade: collectible.grade,
      askingPrice,
      imageUrl: collectible.imageUrl,
      description: collectible.description
        ? sanitizeString(collectible.description, DESCRIPTION_MAX_LENGTH)
        : undefined,
      acceptsOffers: options?.acceptsOffers ?? true,
      minimumOffer: options?.minimumOffer,
      status: 'active',
      views: 0,
      favorites: 0,
      createdAt: Timestamp.now()
    });

    // Update collectible
    batch.update(doc(db, 'collectibles', collectible.id), {
      forSale: true,
      askingPrice,
      updatedAt: Timestamp.now()
    });

    await batch.commit();

    cache.invalidate('marketplace_');
    cache.invalidate(`collectibles_${user.uid}`);
    cache.invalidate(`listed_${collectible.id}`);

    return listingRef.id;
  } catch (error) {
    handleFirestoreError(error, 'Creating collectible listing');
  }
};

// ============================================================================
// OPTIMISTIC UPDATE HELPERS
// ============================================================================

export interface OptimisticUpdate<T> {
  execute: () => Promise<T>;
  rollback: () => void;
}

export function createOptimisticUpdate<T>(
  optimisticFn: () => void,
  executeFn: () => Promise<T>,
  rollbackFn: () => void
): OptimisticUpdate<T> {
  optimisticFn();

  return {
    execute: async () => {
      try {
        return await executeFn();
      } catch (error) {
        rollbackFn();
        throw error;
      }
    },
    rollback: rollbackFn
  };
}

export default app;
