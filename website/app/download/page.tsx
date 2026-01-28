'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';

interface DownloadOption {
  id: string;
  platform: string;
  icon: string;
  name: string;
  version: string;
  size: string;
  downloadUrl: string;
  requirements: string[];
  features: string[];
}

const downloadOptions: DownloadOption[] = [
  {
    id: 'windows',
    platform: 'windows',
    icon: '🪟',
    name: 'Windows Desktop',
    version: '2.5.0',
    size: '156 MB',
    downloadUrl: '/downloads/EPOCGS-Setup-2.5.0.exe',
    requirements: [
      'Windows 10 or later (64-bit)',
      '8 GB RAM minimum',
      '500 MB free disk space',
      'Internet connection for AI grading',
    ],
    features: [
      'Full AI grading with multi-model consensus',
      'Offline collection management',
      'Batch grading up to 100 items',
      'High-resolution image analysis',
      'Direct CGC lookup integration',
      'Auto-sync with cloud account',
    ],
  },
  {
    id: 'macos',
    platform: 'macos',
    icon: '🍎',
    name: 'macOS Desktop',
    version: '2.5.0',
    size: '142 MB',
    downloadUrl: '/downloads/EPOCGS-2.5.0.dmg',
    requirements: [
      'macOS 12 Monterey or later',
      '8 GB RAM minimum',
      '500 MB free disk space',
      'Apple Silicon or Intel processor',
    ],
    features: [
      'Native Apple Silicon support',
      'Full AI grading with multi-model consensus',
      'Offline collection management',
      'Batch grading up to 100 items',
      'High-resolution image analysis',
      'Direct CGC lookup integration',
    ],
  },
  {
    id: 'ios',
    platform: 'ios',
    icon: '📱',
    name: 'iOS App',
    version: '1.2.0',
    size: '45 MB',
    downloadUrl: 'https://apps.apple.com/app/epocgs',
    requirements: [
      'iOS 15.0 or later',
      'iPhone or iPad',
      '100 MB free storage',
    ],
    features: [
      'Quick snap & grade',
      'Cloud sync with desktop',
      'Browse marketplace',
      'Manage collection on-the-go',
      'Push notifications for sales',
    ],
  },
  {
    id: 'android',
    platform: 'android',
    icon: '🤖',
    name: 'Android App',
    version: '1.2.0',
    size: '38 MB',
    downloadUrl: 'https://play.google.com/store/apps/details?id=com.epocgs',
    requirements: [
      'Android 10 or later',
      '100 MB free storage',
    ],
    features: [
      'Quick snap & grade',
      'Cloud sync with desktop',
      'Browse marketplace',
      'Manage collection on-the-go',
      'Push notifications for sales',
    ],
  },
];

const installSteps = [
  {
    step: 1,
    title: 'Download',
    description: 'Click the download button for your platform',
    icon: '⬇️',
  },
  {
    step: 2,
    title: 'Install',
    description: 'Run the installer and follow the prompts',
    icon: '📦',
  },
  {
    step: 3,
    title: 'Sign In',
    description: 'Create an account or sign in with Google',
    icon: '🔐',
  },
  {
    step: 4,
    title: 'Start Grading',
    description: 'Add your first collectible and get an AI grade',
    icon: '🎯',
  },
];

function DownloadCard({ option, isSelected, onSelect }: { option: DownloadOption; isSelected: boolean; onSelect: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`omega-card p-6 cursor-pointer transition-all ${
        isSelected ? 'border-purple-500 shadow-lg shadow-purple-900/30' : ''
      }`}
      onClick={onSelect}
    >
      <div className="flex items-center gap-4 mb-4">
        <span className="text-4xl">{option.icon}</span>
        <div>
          <h3 className="text-xl font-bold text-white">{option.name}</h3>
          <p className="text-sm text-slate-400">v{option.version} - {option.size}</p>
        </div>
      </div>

      {isSelected && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="space-y-4"
        >
          <div>
            <h4 className="text-sm font-semibold text-slate-400 mb-2">Requirements</h4>
            <ul className="space-y-1">
              {option.requirements.map((req, i) => (
                <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                  <span className="text-green-400">✓</span> {req}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-400 mb-2">Features</h4>
            <ul className="space-y-1">
              {option.features.map((feature, i) => (
                <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                  <span className="text-purple-400">★</span> {feature}
                </li>
              ))}
            </ul>
          </div>

          <a
            href={option.downloadUrl}
            className="omega-button w-full text-center block mt-4"
            onClick={(e) => e.stopPropagation()}
          >
            Download for {option.name.split(' ')[0]}
          </a>
        </motion.div>
      )}
    </motion.div>
  );
}

// Pricing tiers
const pricingTiers = [
  {
    name: 'Free',
    price: 0,
    period: 'forever',
    grades: '5 grades/month',
    features: ['Basic AI grading', 'Collection management', '1 device'],
  },
  {
    name: 'Pro',
    price: 9.99,
    period: 'month',
    grades: '100 grades/month',
    features: ['Multi-AI consensus', 'Price estimates', 'Unlimited devices', 'Priority support'],
    popular: true,
  },
  {
    name: 'Unlimited',
    price: 24.99,
    period: 'month',
    grades: 'Unlimited grades',
    features: ['Everything in Pro', 'Batch grading', 'API access', 'Commercial use'],
  },
];

export default function DownloadPage() {
  const [selectedPlatform, setSelectedPlatform] = useState('windows');
  const selectedOption = downloadOptions.find(o => o.id === selectedPlatform)!;

  const handleLaunchDesktop = () => {
    // Try to launch the desktop app via custom protocol
    window.location.href = 'epocgs://launch';
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Hero Section - Desktop App */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="omega-card p-8 mb-12 bg-gradient-to-br from-purple-900/50 to-indigo-900/50 border-purple-500/50"
      >
        <div className="grid md:grid-cols-2 gap-8 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-purple-500/20 rounded-full text-purple-300 text-sm mb-4">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
              Desktop App Available
            </div>
            <h1 className="text-4xl lg:text-5xl font-bold text-white mb-4">
              EPOCGS Desktop
            </h1>
            <p className="text-xl text-slate-300 mb-6">
              Professional AI-powered grading for comics, cards, coins, stamps & vinyl.
              Multi-model consensus from Claude, Gemini & GPT-4.
            </p>
            <div className="flex flex-wrap gap-4">
              <a
                href="/downloads/EPOCGS-Setup-2.5.0.exe"
                className="omega-button text-lg px-8 py-4 flex items-center gap-3"
              >
                <span className="text-2xl">⬇️</span>
                Install Desktop
              </a>
              <button
                onClick={handleLaunchDesktop}
                className="omega-button-secondary text-lg px-8 py-4 flex items-center gap-3 border-2 border-cyan-500/50 hover:bg-cyan-500/20"
              >
                <span className="text-2xl">🚀</span>
                Launch Desktop
              </button>
            </div>
            <p className="text-sm text-slate-400 mt-4">
              Windows 10+ required | v2.5.0 | 156 MB
            </p>
          </div>
          <div className="hidden md:block">
            <div className="relative">
              <div className="w-full h-64 bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg border border-purple-500/30 flex items-center justify-center">
                <div className="text-center">
                  <span className="text-6xl block mb-4">💎</span>
                  <span className="text-white font-bold text-xl">AI Grading Engine</span>
                  <div className="flex justify-center gap-2 mt-3">
                    <span className="px-2 py-1 bg-purple-500/30 rounded text-xs text-purple-300">Claude</span>
                    <span className="px-2 py-1 bg-blue-500/30 rounded text-xs text-blue-300">Gemini</span>
                    <span className="px-2 py-1 bg-green-500/30 rounded text-xs text-green-300">GPT-4</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Pricing Section */}
      <div className="mb-16">
        <h2 className="text-3xl font-bold text-white text-center mb-4">Grading Plans</h2>
        <p className="text-slate-400 text-center mb-8 max-w-2xl mx-auto">
          Choose a plan that fits your grading needs. All plans work across Desktop, Web, and Mobile.
        </p>
        <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          {pricingTiers.map((tier, i) => (
            <motion.div
              key={tier.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`omega-card p-6 relative ${tier.popular ? 'border-2 border-purple-500' : ''}`}
            >
              {tier.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-full text-xs font-bold text-white">
                  MOST POPULAR
                </div>
              )}
              <h3 className="text-xl font-bold text-white mb-2">{tier.name}</h3>
              <div className="mb-4">
                <span className="text-4xl font-bold text-white">${tier.price}</span>
                {tier.price > 0 && <span className="text-slate-400">/{tier.period}</span>}
              </div>
              <div className="text-cyan-400 font-medium mb-4">{tier.grades}</div>
              <ul className="space-y-2 mb-6">
                {tier.features.map((f, j) => (
                  <li key={j} className="text-sm text-slate-300 flex items-center gap-2">
                    <span className="text-green-400">✓</span> {f}
                  </li>
                ))}
              </ul>
              <button className={`w-full py-3 rounded-lg font-semibold transition-all ${
                tier.popular
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:from-purple-500 hover:to-indigo-500'
                  : 'bg-slate-700 text-white hover:bg-slate-600'
              }`}>
                {tier.price === 0 ? 'Get Started' : 'Subscribe'}
              </button>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Header */}
      <div className="text-center mb-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h2 className="text-3xl font-bold text-white mb-4">
            Download for Your Platform
          </h2>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            Available on Windows, macOS, iOS, and Android.
          </p>
        </motion.div>
      </div>

      {/* Platform Selection */}
      <div className="flex flex-wrap justify-center gap-4 mb-8">
        {downloadOptions.map((option) => (
          <button
            key={option.id}
            onClick={() => setSelectedPlatform(option.id)}
            className={`px-6 py-3 rounded-lg text-sm font-medium transition-all ${
              selectedPlatform === option.id
                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-900/50'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            <span className="mr-2">{option.icon}</span>
            {option.name.split(' ')[0]}
          </button>
        ))}
      </div>

      {/* Main Download Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-16">
        {/* Download Card */}
        <motion.div
          key={selectedPlatform}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="omega-card p-8"
        >
          <div className="flex items-center gap-4 mb-6">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center text-4xl">
              {selectedOption.icon}
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">{selectedOption.name}</h2>
              <p className="text-slate-400">Version {selectedOption.version} - {selectedOption.size}</p>
            </div>
          </div>

          <a
            href={selectedOption.downloadUrl}
            className="omega-button w-full text-center block text-lg py-4 mb-6"
          >
            Download Now
          </a>

          <div className="space-y-4">
            <div>
              <h4 className="font-semibold text-white mb-2">System Requirements</h4>
              <ul className="space-y-1">
                {selectedOption.requirements.map((req, i) => (
                  <li key={i} className="text-sm text-slate-400 flex items-center gap-2">
                    <span className="text-green-400 text-xs">●</span> {req}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </motion.div>

        {/* Features Card */}
        <motion.div
          key={`${selectedPlatform}-features`}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="omega-card p-8"
        >
          <h3 className="text-xl font-bold text-white mb-6">What's Included</h3>
          <div className="space-y-4">
            {selectedOption.features.map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/50"
              >
                <span className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400">
                  ✓
                </span>
                <span className="text-slate-200">{feature}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Installation Steps */}
      <div className="mb-16">
        <h2 className="text-2xl font-bold text-white text-center mb-8">
          Quick Start Guide
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {installSteps.map((step, i) => (
            <motion.div
              key={step.step}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="omega-card p-6 text-center relative"
            >
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center text-2xl mx-auto mb-4">
                {step.icon}
              </div>
              <div className="absolute -top-2 -left-2 w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-sm font-bold text-white">
                {step.step}
              </div>
              <h4 className="text-lg font-semibold text-white mb-2">{step.title}</h4>
              <p className="text-sm text-slate-400">{step.description}</p>
            </motion.div>
          ))}
        </div>
      </div>

      {/* All Platforms */}
      <div className="mb-16">
        <h2 className="text-2xl font-bold text-white text-center mb-8">
          Available On All Platforms
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {downloadOptions.map((option, i) => (
            <motion.div
              key={option.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="omega-card p-6 text-center hover:border-purple-500/60 transition-all cursor-pointer"
              onClick={() => setSelectedPlatform(option.id)}
            >
              <span className="text-4xl block mb-3">{option.icon}</span>
              <h4 className="font-semibold text-white mb-1">{option.name}</h4>
              <p className="text-sm text-slate-400 mb-3">v{option.version}</p>
              <a
                href={option.downloadUrl}
                className="omega-button-secondary text-sm px-4 py-2 inline-block"
                onClick={(e) => e.stopPropagation()}
              >
                Download
              </a>
            </motion.div>
          ))}
        </div>
      </div>

      {/* FAQ */}
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold text-white text-center mb-8">
          Frequently Asked Questions
        </h2>
        <div className="space-y-4">
          {[
            {
              q: 'Is EPOCGS free to use?',
              a: 'Yes! The basic version is free with 10 AI grades per month. Premium plans unlock unlimited grading and advanced features.',
            },
            {
              q: 'Do I need an internet connection?',
              a: 'You can manage your collection offline, but AI grading requires an internet connection to access our multi-model consensus system.',
            },
            {
              q: 'How accurate is the AI grading?',
              a: 'Our multi-model consensus (Claude + Gemini + GPT-4) achieves 95%+ correlation with professional grading services like CGC.',
            },
            {
              q: 'Can I sync between devices?',
              a: 'Absolutely! Sign in with the same account on desktop and mobile to keep your collection synced across all devices.',
            },
            {
              q: 'What file formats are supported for grading?',
              a: 'We support JPG, PNG, HEIC, and WebP images. For best results, use high-resolution photos with good lighting.',
            },
          ].map((faq, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="omega-card p-6"
            >
              <h4 className="font-semibold text-white mb-2">{faq.q}</h4>
              <p className="text-slate-400">{faq.a}</p>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Support CTA */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-16 text-center"
      >
        <div className="omega-card p-8 max-w-2xl mx-auto">
          <h3 className="text-xl font-bold text-white mb-4">
            Need Help Installing?
          </h3>
          <p className="text-slate-400 mb-6">
            Our support team is here to help you get started.
            Check out our documentation or reach out directly.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <a href="#" className="omega-button-secondary">View Documentation</a>
            <a href="#" className="omega-button-secondary">Contact Support</a>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
