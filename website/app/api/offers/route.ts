// Offers API Route - Create, Accept, Reject Offers
import { NextRequest, NextResponse } from 'next/server';
import { getAdminDb, FieldValue } from '@/lib/firebase-admin';

// GET - Fetch offers for a listing or user
export async function GET(request: NextRequest) {
  try {
    const db = getAdminDb();
    const { searchParams } = new URL(request.url);
    const listingId = searchParams.get('listingId');
    const userId = searchParams.get('userId');
    const type = searchParams.get('type');

    let query;

    if (listingId) {
      query = db.collection('offers')
        .where('listingId', '==', listingId)
        .where('status', '==', 'pending')
        .orderBy('createdAt', 'desc');
    } else if (userId && type === 'sent') {
      query = db.collection('offers')
        .where('buyerId', '==', userId)
        .orderBy('createdAt', 'desc');
    } else if (userId && type === 'received') {
      query = db.collection('offers')
        .where('sellerId', '==', userId)
        .orderBy('createdAt', 'desc');
    } else {
      return NextResponse.json({ error: 'Missing listingId or userId' }, { status: 400 });
    }

    const snapshot = await query.get();
    const offers = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data(),
      createdAt: doc.data().createdAt?.toDate?.() || doc.data().createdAt,
    }));

    return NextResponse.json({ offers });
  } catch (error: any) {
    console.error('Error fetching offers:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

// POST - Create a new offer
export async function POST(request: NextRequest) {
  try {
    const db = getAdminDb();
    const body = await request.json();
    const { listingId, sellerId, buyerId, buyerName, buyerAvatar, amount, message, listingTitle, listingImage } = body;

    if (!listingId || !sellerId || !buyerId || !amount) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const existingOffer = await db.collection('offers')
      .where('listingId', '==', listingId)
      .where('buyerId', '==', buyerId)
      .where('status', '==', 'pending')
      .get();

    if (!existingOffer.empty) {
      return NextResponse.json({ error: 'You already have a pending offer' }, { status: 400 });
    }

    const offerRef = await db.collection('offers').add({
      listingId,
      sellerId,
      buyerId,
      buyerName: buyerName || 'Anonymous',
      buyerAvatar,
      amount,
      message: message || '',
      listingTitle,
      listingImage,
      status: 'pending',
      createdAt: FieldValue.serverTimestamp(),
    });

    await db.collection('notifications').add({
      userId: sellerId,
      type: 'offer',
      title: 'New Offer Received!',
      message: (buyerName || 'Someone') + ' offered $' + amount + ' for ' + listingTitle,
      listingId,
      offerId: offerRef.id,
      read: false,
      createdAt: FieldValue.serverTimestamp(),
    });

    return NextResponse.json({
      success: true,
      offerId: offerRef.id,
      message: 'Offer submitted successfully'
    });
  } catch (error: any) {
    console.error('Error creating offer:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

// PATCH - Accept or reject an offer
export async function PATCH(request: NextRequest) {
  try {
    const db = getAdminDb();
    const body = await request.json();
    const { offerId, action, userId } = body;

    if (!offerId || !action || !userId) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const offerRef = db.collection('offers').doc(offerId);
    const offerDoc = await offerRef.get();

    if (!offerDoc.exists) {
      return NextResponse.json({ error: 'Offer not found' }, { status: 404 });
    }

    const offer = offerDoc.data();

    if (offer?.sellerId !== userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
    }

    if (action === 'accept') {
      await offerRef.update({
        status: 'accepted',
        acceptedAt: FieldValue.serverTimestamp(),
      });

      const otherOffers = await db.collection('offers')
        .where('listingId', '==', offer?.listingId)
        .where('status', '==', 'pending')
        .get();

      const batch = db.batch();
      otherOffers.docs.forEach(doc => {
        if (doc.id !== offerId) {
          batch.update(doc.ref, { status: 'rejected', rejectedAt: FieldValue.serverTimestamp() });
        }
      });
      await batch.commit();

      await db.collection('notifications').add({
        userId: offer?.buyerId,
        type: 'offer_accepted',
        title: 'Offer Accepted!',
        message: 'Your offer of $' + offer?.amount + ' was accepted!',
        listingId: offer?.listingId,
        offerId,
        read: false,
        createdAt: FieldValue.serverTimestamp(),
      });

      return NextResponse.json({
        success: true,
        message: 'Offer accepted'
      });
    } else if (action === 'reject') {
      await offerRef.update({
        status: 'rejected',
        rejectedAt: FieldValue.serverTimestamp(),
      });

      await db.collection('notifications').add({
        userId: offer?.buyerId,
        type: 'offer_rejected',
        title: 'Offer Declined',
        message: 'Your offer of $' + offer?.amount + ' was declined.',
        listingId: offer?.listingId,
        offerId,
        read: false,
        createdAt: FieldValue.serverTimestamp(),
      });

      return NextResponse.json({ success: true, message: 'Offer rejected' });
    } else if (action === 'counter') {
      const { counterAmount } = body;
      if (!counterAmount) {
        return NextResponse.json({ error: 'Counter amount required' }, { status: 400 });
      }

      await offerRef.update({
        status: 'countered',
        counterAmount,
        counteredAt: FieldValue.serverTimestamp(),
      });

      await db.collection('notifications').add({
        userId: offer?.buyerId,
        type: 'counter_offer',
        title: 'Counter Offer Received',
        message: 'Seller countered with $' + counterAmount,
        listingId: offer?.listingId,
        offerId,
        read: false,
        createdAt: FieldValue.serverTimestamp(),
      });

      return NextResponse.json({ success: true, message: 'Counter offer sent' });
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  } catch (error: any) {
    console.error('Error updating offer:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
