'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';

const features = [
  {
    icon: '🎯',
    title: 'AI-Powered Grading',
    description: 'Multi-model consensus using Claude, Gemini, and GPT for accurate grades',
  },
  {
    icon: '📱',
    title: 'Cross-Platform Sync',
    description: 'Your collection syncs across desktop, web, and mobile apps',
  },
  {
    icon: '🏪',
    title: 'Marketplace',
    description: 'Buy and sell collectibles with other verified users',
  },
  {
    icon: '🔐',
    title: 'Secure Storage',
    description: 'Firebase-backed cloud storage with enterprise security',
  },
  {
    icon: '🤖',
    title: 'AI Personalities',
    description: 'Get commentary from BREE, RAISTLIN, SAGE, and more',
  },
  {
    icon: '📊',
    title: 'Market Analytics',
    description: 'Real-time pricing data and market trends',
  },
];

const collectibleTypes = [
  { name: 'Comics', icon: '📚', count: '10,000+' },
  { name: 'Trading Cards', icon: '🎴', count: '50,000+' },
  { name: 'Coins', icon: '🪙', count: '5,000+' },
  { name: 'Stamps', icon: '📮', count: '3,000+' },
  { name: 'Vinyl', icon: '💿', count: '2,000+' },
];

export default function HomePage() {
  return (
    <div className="relative">
      {/* Hero Section */}
      <section className="relative py-20 lg:py-32 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-gradient-to-b from-purple-900/20 to-transparent" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-600/10 rounded-full blur-3xl" />

        <div className="container mx-auto px-4 relative">
          <div className="max-w-4xl mx-auto text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-500/20 border border-purple-500/30 mb-8">
                <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                <span className="text-sm text-purple-300">Authority Level 11.0 SOVEREIGN</span>
              </div>

              <h1 className="text-5xl lg:text-7xl font-bold mb-6">
                <span className="bg-gradient-to-r from-purple-400 via-cyan-400 to-purple-400 bg-clip-text text-transparent">
                  EPOCGS
                </span>
              </h1>

              <p className="text-xl lg:text-2xl text-slate-300 mb-4">
                Echo Prime Omega Collectibles Grading System
              </p>

              <p className="text-lg text-slate-400 mb-8 max-w-2xl mx-auto">
                AI-powered grading for comics, trading cards, coins, stamps, and vinyl.
                Multi-model consensus. Real-time marketplace. Cloud sync across all devices.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-4">
                <Link href="/download" className="omega-button text-lg px-8 py-4">
                  Download Desktop App
                </Link>
                <Link href="/marketplace" className="omega-button-secondary text-lg px-8 py-4">
                  Browse Marketplace
                </Link>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 border-y border-purple-500/20 bg-slate-900/50">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
            {collectibleTypes.map((type, index) => (
              <motion.div
                key={type.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                className="omega-card p-6 text-center"
              >
                <div className="text-4xl mb-2">{type.icon}</div>
                <div className="text-2xl font-bold text-white">{type.count}</div>
                <div className="text-sm text-slate-400">{type.name} Graded</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">
              Powered by Advanced AI
            </h2>
            <p className="text-slate-400 max-w-2xl mx-auto">
              Our multi-model consensus system ensures accurate, consistent grading across all collectible types
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                className="omega-card p-6"
              >
                <div className="text-4xl mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-slate-400">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 relative">
        <div className="absolute inset-0 bg-gradient-to-t from-purple-900/20 to-transparent" />
        <div className="container mx-auto px-4 relative">
          <div className="omega-card p-12 text-center max-w-3xl mx-auto">
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to Grade Your Collection?
            </h2>
            <p className="text-slate-400 mb-8">
              Download the desktop app for the full experience, or use the web app to manage your collection anywhere.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <Link href="/download" className="omega-button">
                Get Started Free
              </Link>
              <Link href="/showcase" className="omega-button-secondary">
                View Showcase
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
