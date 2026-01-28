'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import Link from 'next/link';

// Service tiers for voice cloning
const serviceTiers = [
  {
    id: 'basic',
    name: 'Basic Clone',
    price: 99,
    description: 'Standard voice clone from your audio samples',
    features: [
      'Clone from 5+ minutes of audio',
      'API access included',
      '10,000 character credits',
      '3-day turnaround',
      'Email support',
    ],
    popular: false,
  },
  {
    id: 'pro',
    name: 'Professional Clone',
    price: 249,
    description: 'High-quality clone with fine-tuning',
    features: [
      'Clone from 30+ minutes of audio',
      'Professional fine-tuning',
      'API access included',
      '50,000 character credits',
      '24-hour turnaround',
      'Priority support',
      'Multiple voice variations',
    ],
    popular: true,
  },
  {
    id: 'custom',
    name: 'Custom Creation',
    price: 499,
    description: 'Unique voice designed to your specifications',
    features: [
      'Custom voice from description',
      'Unlimited revisions',
      'API access included',
      '200,000 character credits',
      'Dedicated support',
      'Commercial license',
      'Exclusive rights option',
    ],
    popular: false,
  },
];

// Credit packs for API usage
const creditPacks = [
  { id: 'starter', name: 'Starter', characters: 10000, price: 15 },
  { id: 'pro', name: 'Pro', characters: 50000, price: 50 },
  { id: 'business', name: 'Business', characters: 200000, price: 150 },
];

function ServiceCard({ tier, onSelect }: { tier: typeof serviceTiers[0]; onSelect: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`omega-card p-6 relative ${tier.popular ? 'border-2 border-purple-500' : ''}`}
    >
      {tier.popular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-full text-xs font-bold text-white">
          MOST POPULAR
        </div>
      )}

      <div className="text-center mb-6">
        <h3 className="text-xl font-bold text-white mb-2">{tier.name}</h3>
        <div className="text-4xl font-bold text-white mb-2">
          ${tier.price}
        </div>
        <p className="text-sm text-slate-400">{tier.description}</p>
      </div>

      <ul className="space-y-3 mb-6">
        {tier.features.map((feature, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <span className="text-green-400 mt-0.5">✓</span>
            <span className="text-slate-300">{feature}</span>
          </li>
        ))}
      </ul>

      <button
        onClick={onSelect}
        className={`w-full py-3 rounded-lg font-semibold transition-all ${
          tier.popular
            ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:from-purple-500 hover:to-indigo-500'
            : 'bg-slate-700 text-white hover:bg-slate-600'
        }`}
      >
        Get Started
      </button>
    </motion.div>
  );
}

export default function ServicesPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'cloning' | 'credits'>('cloning');

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-12">
        <motion.h1
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl md:text-5xl font-bold text-white mb-4"
        >
          Voice Cloning Services
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-xl text-slate-400 max-w-2xl mx-auto"
        >
          Professional voice cloning with API access. Create custom voices or clone your own.
        </motion.p>
      </div>

      {/* Tab Switcher */}
      <div className="flex justify-center gap-2 mb-8">
        <button
          onClick={() => setActiveTab('cloning')}
          className={`px-6 py-3 rounded-lg font-medium transition-all ${
            activeTab === 'cloning'
              ? 'bg-purple-600 text-white'
              : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
          }`}
        >
          🎙️ Voice Cloning
        </button>
        <button
          onClick={() => setActiveTab('credits')}
          className={`px-6 py-3 rounded-lg font-medium transition-all ${
            activeTab === 'credits'
              ? 'bg-purple-600 text-white'
              : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
          }`}
        >
          💳 API Credits
        </button>
      </div>

      {activeTab === 'cloning' ? (
        <>
          {/* Service Tiers */}
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto mb-16">
            {serviceTiers.map((tier, i) => (
              <motion.div
                key={tier.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <ServiceCard
                  tier={tier}
                  onSelect={() => router.push(`/services/${tier.id}`)}
                />
              </motion.div>
            ))}
          </div>

          {/* How It Works */}
          <div className="max-w-4xl mx-auto mb-16">
            <h2 className="text-2xl font-bold text-white text-center mb-8">How It Works</h2>
            <div className="grid md:grid-cols-4 gap-6">
              {[
                { step: 1, icon: '📤', title: 'Submit Request', desc: 'Choose a tier and upload audio samples' },
                { step: 2, icon: '🎛️', title: 'We Clone It', desc: 'Our team creates your voice clone' },
                { step: 3, icon: '✅', title: 'Review & Approve', desc: 'Listen and request revisions' },
                { step: 4, icon: '🔌', title: 'API Access', desc: 'Use your voice via our API' },
              ].map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + i * 0.1 }}
                  className="text-center"
                >
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-800 flex items-center justify-center text-3xl">
                    {item.icon}
                  </div>
                  <div className="text-xs text-purple-400 font-semibold mb-1">STEP {item.step}</div>
                  <h3 className="text-white font-semibold mb-1">{item.title}</h3>
                  <p className="text-sm text-slate-400">{item.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Sample Voice */}
          <div className="max-w-2xl mx-auto mb-16">
            <div className="omega-card p-6">
              <h3 className="text-lg font-semibold text-white mb-4 text-center">
                🎧 Sample Voice Clone
              </h3>
              <div className="bg-slate-800 rounded-lg p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-r from-purple-600 to-indigo-600 flex items-center justify-center">
                    <span className="text-xl">🎙️</span>
                  </div>
                  <div>
                    <div className="text-white font-medium">Echo Prime Voice</div>
                    <div className="text-sm text-slate-400">Professional AI Voice Clone</div>
                  </div>
                </div>
                <button className="px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-white text-sm font-medium transition-colors">
                  ▶ Play Sample
                </button>
              </div>
            </div>
          </div>
        </>
      ) : (
        <>
          {/* Credit Packs */}
          <div className="max-w-4xl mx-auto mb-16">
            <h2 className="text-2xl font-bold text-white text-center mb-8">API Credit Packs</h2>
            <p className="text-slate-400 text-center mb-8 max-w-2xl mx-auto">
              Purchase credits to use the Voice API. Credits are used per character of text converted to speech.
            </p>

            <div className="grid md:grid-cols-3 gap-6">
              {creditPacks.map((pack, i) => (
                <motion.div
                  key={pack.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="omega-card p-6 text-center"
                >
                  <h3 className="text-xl font-bold text-white mb-2">{pack.name}</h3>
                  <div className="text-4xl font-bold text-green-400 mb-2">
                    ${pack.price}
                  </div>
                  <div className="text-slate-400 mb-4">
                    {pack.characters.toLocaleString()} characters
                  </div>
                  <div className="text-xs text-slate-500 mb-4">
                    ${(pack.price / pack.characters * 1000).toFixed(2)} per 1K chars
                  </div>
                  <button className="w-full py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-white font-medium transition-colors">
                    Buy Credits
                  </button>
                </motion.div>
              ))}
            </div>
          </div>

          {/* API Info */}
          <div className="max-w-3xl mx-auto">
            <div className="omega-card p-6">
              <h3 className="text-lg font-semibold text-white mb-4">🔌 Voice API</h3>
              <p className="text-slate-400 mb-4">
                After purchasing a voice clone service, you'll receive API access to generate speech with your cloned voice.
              </p>
              <div className="bg-slate-900 rounded-lg p-4 font-mono text-sm overflow-x-auto">
                <div className="text-slate-500"># Generate speech with your API key</div>
                <div className="text-green-400">
                  curl -X POST https://echo-op.com/api/voice/generate \
                </div>
                <div className="text-slate-400 pl-4">
                  -H "X-API-Key: your_api_key" \
                </div>
                <div className="text-slate-400 pl-4">
                  -d '{`{"text": "Hello world", "voice": "your_voice_id"}`}'
                </div>
              </div>
              <div className="mt-4 flex gap-3">
                <button className="px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-white text-sm font-medium transition-colors">
                  View API Docs
                </button>
                <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white text-sm font-medium transition-colors">
                  Get API Key
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* FAQ Section */}
      <div className="max-w-3xl mx-auto mt-16">
        <h2 className="text-2xl font-bold text-white text-center mb-8">Frequently Asked Questions</h2>
        <div className="space-y-4">
          {[
            {
              q: 'How long does voice cloning take?',
              a: 'Basic clones are delivered within 3 days. Professional clones within 24 hours. Custom creations vary based on complexity.',
            },
            {
              q: 'What audio quality do I need?',
              a: 'We recommend high-quality recordings without background noise. Minimum 5 minutes for basic, 30 minutes for professional quality.',
            },
            {
              q: 'Can I use the cloned voice commercially?',
              a: 'Yes! All tiers include API access. Commercial license is included with the Custom tier or available as an add-on.',
            },
            {
              q: 'How does the API work?',
              a: 'After your voice is cloned, you receive an API key. Send text to our API endpoint and receive audio in return. Credits are deducted per character.',
            },
          ].map((faq, i) => (
            <div key={i} className="omega-card p-4">
              <h4 className="text-white font-medium mb-2">{faq.q}</h4>
              <p className="text-sm text-slate-400">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Back to Marketplace */}
      <div className="text-center mt-12">
        <Link href="/marketplace" className="text-purple-400 hover:text-purple-300 transition-colors">
          ← Back to Marketplace
        </Link>
      </div>
    </div>
  );
}
