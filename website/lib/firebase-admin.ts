// Firebase Admin SDK - Lazy initialization for Vercel builds
import { initializeApp, getApps, cert } from 'firebase-admin/app';
import { getFirestore, Firestore } from 'firebase-admin/firestore';

let adminDb: Firestore | null = null;

export function getAdminDb(): Firestore {
  if (adminDb) return adminDb;

  if (!getApps().length) {
    const privateKey = process.env.FIREBASE_PRIVATE_KEY;
    if (!privateKey) {
      throw new Error('FIREBASE_PRIVATE_KEY not configured');
    }

    initializeApp({
      credential: cert({
        projectId: process.env.FIREBASE_PROJECT_ID || 'echo-prime-ai',
        clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
        privateKey: privateKey.replace(/\\n/g, '\n'),
      }),
    });
  }

  adminDb = getFirestore();
  return adminDb;
}

export { FieldValue } from 'firebase-admin/firestore';
