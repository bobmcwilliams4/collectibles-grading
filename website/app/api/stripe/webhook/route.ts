// Stripe Webhook Handler
import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { getAdminDb } from '@/lib/firebase-admin';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '');
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET || '';

export async function POST(request: NextRequest) {
  try {
    const db = getAdminDb();
    const body = await request.text();
    const sig = request.headers.get('stripe-signature');

    if (!sig) {
      return NextResponse.json({ error: 'No signature' }, { status: 400 });
    }

    let event: Stripe.Event;

    try {
      event = stripe.webhooks.constructEvent(body, sig, webhookSecret);
    } catch (err: any) {
      console.error('Webhook signature verification failed:', err.message);
      return NextResponse.json({ error: `Webhook Error: ${err.message}` }, { status: 400 });
    }

    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session;
        const metadata = session.metadata;

        if (metadata) {
          const { listingId, sellerId, buyerId, platformFee, sellerPayout } = metadata;

          await db.collection('transactions').add({
            listingId,
            sellerId,
            buyerId,
            amount: session.amount_total,
            platformFee: parseInt(platformFee || '0'),
            sellerPayout: parseInt(sellerPayout || '0'),
            stripeSessionId: session.id,
            stripePaymentIntent: session.payment_intent,
            status: 'completed',
            createdAt: new Date(),
          });

          await db.collection('marketplace').doc(listingId).update({
            status: 'sold',
            soldAt: new Date(),
            buyerId,
          });

          await db.collection('notifications').add({
            userId: sellerId,
            type: 'sale',
            title: 'Item Sold!',
            message: `Your item has been purchased for $${(session.amount_total || 0) / 100}`,
            listingId,
            read: false,
            createdAt: new Date(),
          });
        }
        break;
      }

      case 'payment_intent.payment_failed': {
        const paymentIntent = event.data.object as Stripe.PaymentIntent;
        console.log('Payment failed:', paymentIntent.id);
        break;
      }

      default:
        console.log(`Unhandled event type: ${event.type}`);
    }

    return NextResponse.json({ received: true });
  } catch (error: any) {
    console.error('Webhook error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
