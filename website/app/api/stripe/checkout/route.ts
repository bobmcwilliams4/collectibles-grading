// Stripe Checkout API Route
import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || 'sk_test_your_key_here');

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { listingId, title, price, imageUrl, sellerId, buyerId, category, type } = body;

    if (!listingId || !title || !price || !sellerId || !buyerId) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    // Calculate amounts (price is in dollars, Stripe needs cents)
    const amountCents = Math.round(price * 100);
    const platformFeeCents = Math.round(amountCents * 0.05); // 5% platform fee
    const sellerPayoutCents = amountCents - platformFeeCents;

    // Create Stripe Checkout Session
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      line_items: [
        {
          price_data: {
            currency: 'usd',
            product_data: {
              name: title,
              description: `${category === 'collectibles' ? 'Collectible' : 'Digital'} - ${type}`,
              images: imageUrl ? [imageUrl] : [],
            },
            unit_amount: amountCents,
          },
          quantity: 1,
        },
      ],
      mode: 'payment',
      success_url: `${process.env.NEXT_PUBLIC_BASE_URL || 'https://echo-op.com'}/marketplace/${listingId}?success=true`,
      cancel_url: `${process.env.NEXT_PUBLIC_BASE_URL || 'https://echo-op.com'}/marketplace/${listingId}?canceled=true`,
      metadata: {
        listingId,
        sellerId,
        buyerId,
        category,
        type,
        platformFee: platformFeeCents.toString(),
        sellerPayout: sellerPayoutCents.toString(),
      },
    });

    return NextResponse.json({ sessionId: session.id, url: session.url });
  } catch (error: any) {
    console.error('Stripe checkout error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
