// Stripe Configuration for EPOCGS Marketplace
import { loadStripe, Stripe } from '@stripe/stripe-js';

// Stripe publishable key - replace with your actual key
const STRIPE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || 'pk_test_your_key_here';

let stripePromise: Promise<Stripe | null>;

export const getStripe = () => {
  if (!stripePromise) {
    stripePromise = loadStripe(STRIPE_PUBLISHABLE_KEY);
  }
  return stripePromise;
};

// Platform fee percentage (ECHO OMEGA PRIME takes 5%)
export const PLATFORM_FEE_PERCENT = 5;

// Calculate platform fee
export const calculatePlatformFee = (amount: number): number => {
  return Math.round(amount * (PLATFORM_FEE_PERCENT / 100));
};

// Calculate seller payout
export const calculateSellerPayout = (amount: number): number => {
  return amount - calculatePlatformFee(amount);
};

// Format price for display
export const formatPrice = (cents: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(cents / 100);
};

// Convert dollars to cents
export const dollarsToCents = (dollars: number): number => {
  return Math.round(dollars * 100);
};

// Convert cents to dollars
export const centsToDollars = (cents: number): number => {
  return cents / 100;
};
