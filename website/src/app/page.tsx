'use client';
import { useState } from 'react';

interface PricingTier {
  name: string;
  price: number;
  period: string;
  popular?: boolean;
  features: string[];
}

const PRICING: Record<string, PricingTier> = {
  free: { name: 'Free', price: 0, period: '', features: ['3 AI grades/month', 'Device TTS only', '1 collection (25 items)', 'Basic grade display', 'Marketplace browsing'] },
  pro: { name: 'Pro', price: 9.99, period: '/month', popular: true, features: ['50 AI grades/month', 'BREE voice (30 TTS/mo)', 'Unlimited collections', 'Full grade breakdown', 'Sell on marketplace (5)', 'Price alerts (10)', 'PDF/CSV exports', 'Counterfeit detection (5/mo)'] },
  master: { name: 'Master', price: 24.99, period: '/month', features: ['200 AI grades/month', 'Unlimited TTS voices', 'Priority grading queue', 'Unlimited marketplace', 'API access', 'Batch grading (10)', 'Insurance reports', 'Market analytics', 'Priority support'] },
};

const FEATURES = [
  { icon: '📷', title: 'AI Vision Grading', desc: 'Snap a photo and get instant CGC/PSA-style grades using advanced AI vision.' },
  { icon: '🎙️', title: 'Voice Commentary', desc: 'BREE and Raistlin provide sassy or wise commentary on your grades.' },
  { icon: '💰', title: 'Market Pricing', desc: 'Real-time valuations based on recent eBay and Heritage auction sales.' },
  { icon: '🔍', title: 'Counterfeit Detection', desc: 'AI-powered authenticity checking for peace of mind.' },
  { icon: '📊', title: 'Collection Analytics', desc: 'Track your portfolio value with beautiful charts and insights.' },
  { icon: '🛒', title: 'Marketplace', desc: 'Buy and sell graded collectibles directly in the app.' },
];

const TESTIMONIALS = [
  { name: 'Mike R.', role: 'Comic Collector', text: 'EPOCGS graded my Amazing Spider-Man #300 at 9.4 - CGC later confirmed 9.2. Incredibly accurate!', rating: 5 },
  { name: 'Sarah L.', role: 'Card Dealer', text: 'The batch grading feature saves me hours. I can grade 50 cards in minutes instead of days.', rating: 5 },
  { name: 'Dave K.', role: 'Coin Enthusiast', text: "BREE's commentary cracks me up every time. 'Holy crap, that's a beauty!' Never gets old.", rating: 5 },
];

const FAQ = [
  { q: 'How accurate is the AI grading?', a: 'Our AI achieves 92% accuracy within 0.5 grade points compared to CGC/PSA professional grades. We use Gemini Vision trained on thousands of graded examples.' },
  { q: 'What collectibles can I grade?', a: 'Comics, trading cards (Pokemon, MTG, sports), coins, stamps, and vinyl records. More categories coming soon!' },
  { q: 'Can I cancel my subscription?', a: 'Yes, cancel anytime. Your collection data remains accessible on the free tier.' },
  { q: 'Is my collection data secure?', a: 'Absolutely. We use Firebase with enterprise-grade security. Your data is encrypted and never shared.' },
];

export default function LandingPage() {
  const [annual, setAnnual] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a1a] via-[#1a1a2e] to-[#0a0a1a] text-white">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-[#0a0a1a]/80 backdrop-blur-lg border-b border-amber-500/20">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <span className="text-3xl">💎</span>
            <span className="text-2xl font-bold text-amber-400">EPOCGS</span>
          </div>
          <div className="hidden md:flex gap-8 text-gray-300">
            <a href="#features" className="hover:text-amber-400 transition">Features</a>
            <a href="#pricing" className="hover:text-amber-400 transition">Pricing</a>
            <a href="#faq" className="hover:text-amber-400 transition">FAQ</a>
          </div>
          <a href="https://apps.apple.com/app/collectibles-grader" className="bg-amber-500 hover:bg-amber-400 text-black font-bold px-6 py-2 rounded-full transition">
            Download App
          </a>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <span className="bg-amber-500/20 text-amber-400 px-4 py-2 rounded-full text-sm font-medium">
            AI-Powered Collectibles Grading
          </span>
          <h1 className="text-5xl md:text-7xl font-bold mt-6 mb-6 bg-gradient-to-r from-amber-400 via-yellow-300 to-amber-500 bg-clip-text text-transparent">
            Grade Your Collection<br />Like a Pro
          </h1>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10">
            Snap a photo. Get an instant CGC/PSA-style grade. Know your collection's true value in seconds with AI-powered grading.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <a href="https://apps.apple.com/app/collectibles-grader" className="bg-amber-500 hover:bg-amber-400 text-black font-bold px-8 py-4 rounded-full text-lg flex items-center gap-2 transition transform hover:scale-105">
              🍎 Download for iOS
            </a>
            <a href="#demo" className="border-2 border-amber-500 text-amber-400 hover:bg-amber-500/10 font-bold px-8 py-4 rounded-full text-lg flex items-center gap-2 transition">
              ▶️ Watch Demo
            </a>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="py-12 border-y border-amber-500/20 bg-[#1a1a2e]/50">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          <div><div className="text-3xl md:text-4xl font-bold text-amber-400">50K+</div><div className="text-gray-400 mt-1">Items Graded</div></div>
          <div><div className="text-3xl md:text-4xl font-bold text-amber-400">92%</div><div className="text-gray-400 mt-1">Accuracy Rate</div></div>
          <div><div className="text-3xl md:text-4xl font-bold text-amber-400">4.9★</div><div className="text-gray-400 mt-1">App Store Rating</div></div>
          <div><div className="text-3xl md:text-4xl font-bold text-amber-400">10K+</div><div className="text-gray-400 mt-1">Active Users</div></div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">Everything You Need</h2>
            <p className="text-xl text-gray-400">Professional grading tools in your pocket</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {FEATURES.map((f, i) => (
              <div key={i} className="bg-[#1a1a2e] border border-amber-500/20 rounded-2xl p-8 hover:border-amber-500/50 transition">
                <div className="text-5xl mb-4">{f.icon}</div>
                <h3 className="text-xl font-bold mb-2">{f.title}</h3>
                <p className="text-gray-400">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24 px-6 bg-[#1a1a2e]/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">How It Works</h2>
            <p className="text-xl text-gray-400">Grade your collectibles in 3 simple steps</p>
          </div>
          <div className="grid md:grid-cols-3 gap-12">
            <div className="text-center">
              <div className="w-20 h-20 bg-amber-500 rounded-full flex items-center justify-center text-3xl font-bold text-black mx-auto mb-6">1</div>
              <h3 className="text-2xl font-bold mb-2">Snap a Photo</h3>
              <p className="text-gray-400">Take a clear photo of your comic, card, or coin using your phone camera.</p>
            </div>
            <div className="text-center">
              <div className="w-20 h-20 bg-amber-500 rounded-full flex items-center justify-center text-3xl font-bold text-black mx-auto mb-6">2</div>
              <h3 className="text-2xl font-bold mb-2">AI Analysis</h3>
              <p className="text-gray-400">Our Gemini Vision AI analyzes condition, defects, and assigns a grade.</p>
            </div>
            <div className="text-center">
              <div className="w-20 h-20 bg-amber-500 rounded-full flex items-center justify-center text-3xl font-bold text-black mx-auto mb-6">3</div>
              <h3 className="text-2xl font-bold mb-2">Get Results</h3>
              <p className="text-gray-400">Receive your grade, market value, and optional voice commentary instantly.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">Simple Pricing</h2>
            <p className="text-xl text-gray-400 mb-8">Start free. Upgrade when you're ready.</p>
            <div className="flex items-center justify-center gap-4">
              <span className={annual ? 'text-gray-400' : 'text-white font-bold'}>Monthly</span>
              <button onClick={() => setAnnual(!annual)} className="w-14 h-8 bg-amber-500/30 rounded-full relative">
                <div className={`w-6 h-6 bg-amber-500 rounded-full absolute top-1 transition-all ${annual ? 'left-7' : 'left-1'}`}></div>
              </button>
              <span className={annual ? 'text-white font-bold' : 'text-gray-400'}>Annual <span className="text-emerald-400">(Save 33%)</span></span>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {Object.entries(PRICING).map(([key, tier]) => (
              <div key={key} className={`rounded-2xl p-8 ${tier.popular ? 'bg-gradient-to-b from-amber-500/20 to-[#1a1a2e] border-2 border-amber-500 scale-105' : 'bg-[#1a1a2e] border border-gray-700'}`}>
                {tier.popular && <div className="text-amber-400 text-sm font-bold text-center mb-4">MOST POPULAR</div>}
                <h3 className="text-2xl font-bold">{tier.name}</h3>
                <div className="mt-4 mb-6">
                  <span className="text-4xl font-bold">${annual && tier.price > 0 ? (tier.price * 0.67).toFixed(2) : tier.price}</span>
                  <span className="text-gray-400">{tier.period}</span>
                  {annual && tier.price > 0 && <div className="text-sm text-emerald-400">Billed ${(tier.price * 12 * 0.67).toFixed(0)}/year</div>}
                </div>
                <ul className="space-y-3 mb-8">
                  {tier.features.map((f, j) => (
                    <li key={j} className="flex items-start gap-2">
                      <span className="text-amber-400">✓</span>
                      <span className="text-gray-300">{f}</span>
                    </li>
                  ))}
                </ul>
                <button className={`w-full py-3 rounded-full font-bold transition ${tier.popular ? 'bg-amber-500 hover:bg-amber-400 text-black' : 'border-2 border-amber-500 text-amber-400 hover:bg-amber-500/10'}`}>
                  {tier.price === 0 ? 'Get Started Free' : 'Start 7-Day Trial'}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-24 px-6 bg-[#1a1a2e]/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">Loved by Collectors</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {TESTIMONIALS.map((t, i) => (
              <div key={i} className="bg-[#1a1a2e] border border-amber-500/20 rounded-2xl p-8">
                <div className="text-amber-400 mb-4">{'★'.repeat(t.rating)}</div>
                <p className="text-gray-300 mb-6 italic">"{t.text}"</p>
                <div className="font-bold">{t.name}</div>
                <div className="text-gray-500 text-sm">{t.role}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="py-24 px-6">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">FAQ</h2>
          </div>
          <div className="space-y-4">
            {FAQ.map((f, i) => (
              <div key={i} className="bg-[#1a1a2e] border border-amber-500/20 rounded-xl overflow-hidden">
                <button onClick={() => setOpenFaq(openFaq === i ? null : i)} className="w-full px-6 py-4 text-left font-bold flex justify-between items-center">
                  {f.q}
                  <span className={`transform transition ${openFaq === i ? 'rotate-180' : ''}`}>▼</span>
                </button>
                {openFaq === i && <div className="px-6 pb-4 text-gray-400">{f.a}</div>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto text-center bg-gradient-to-r from-amber-500/20 via-purple-500/20 to-amber-500/20 rounded-3xl p-12 border border-amber-500/30">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">Ready to Grade?</h2>
          <p className="text-xl text-gray-400 mb-8">Download EPOCGS free and start grading your collection today.</p>
          <a href="https://apps.apple.com/app/collectibles-grader" className="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-400 text-black font-bold px-10 py-5 rounded-full text-xl transition transform hover:scale-105">
            🍎 Download for iOS
          </a>
          <p className="text-gray-500 mt-4">Android coming soon</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-amber-500/20">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex items-center gap-2">
            <span className="text-2xl">💎</span>
            <span className="text-xl font-bold text-amber-400">EPOCGS</span>
          </div>
          <div className="flex gap-8 text-gray-400">
            <a href="/privacy" className="hover:text-amber-400 transition">Privacy</a>
            <a href="/terms" className="hover:text-amber-400 transition">Terms</a>
            <a href="mailto:support@echo-op.com" className="hover:text-amber-400 transition">Contact</a>
          </div>
          <div className="text-gray-500">© 2026 Echo Omega Prime. All rights reserved.</div>
        </div>
      </footer>
    </div>
  );
}
