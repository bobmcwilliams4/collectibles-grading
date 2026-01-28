'use client';

export default function TermsPage() {
  return (
    <div className="container mx-auto px-4 py-12 max-w-4xl">
      <h1 className="text-4xl font-bold text-white mb-8">Terms of Service</h1>
      <div className="prose prose-invert prose-purple max-w-none space-y-6 text-slate-300">
        <p className="text-slate-400">Last updated: January 4, 2026</p>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">1. Acceptance of Terms</h2>
          <p>
            By accessing or using EPOCGS (&quot;Echo Prime Omega Collectibles Grading System&quot;),
            you agree to be bound by these Terms of Service. If you do not agree to these terms,
            do not use the service.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">2. Description of Service</h2>
          <p>EPOCGS provides:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li>AI-powered grading for collectibles (comics, cards, coins, stamps, vinyl).</li>
            <li>Collection management and cloud synchronization.</li>
            <li>Marketplace for buying and selling graded collectibles.</li>
            <li>Voice commentary and text-to-speech features.</li>
            <li>Market pricing analysis and valuations.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">3. AI Grading Disclaimer</h2>
          <p>
            <strong>Important:</strong> AI grades provided by EPOCGS are estimates based on visual
            analysis and should not be considered official grades. Our AI achieves approximately
            92% accuracy within 0.5 grade points compared to professional grading services (CGC, PSA).
          </p>
          <p className="mt-4">
            EPOCGS grades are:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>For personal reference and collection management only.</li>
            <li>Not a substitute for professional grading services.</li>
            <li>Not guaranteed to match official grades.</li>
            <li>Subject to limitations of photographic analysis.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">4. Subscription Tiers</h2>
          <p>EPOCGS offers three subscription tiers:</p>
          <div className="bg-slate-800/50 rounded-lg p-6 mt-4">
            <h3 className="text-lg font-semibold text-amber-400">Free Tier</h3>
            <ul className="list-disc pl-6 mt-2 space-y-1">
              <li>3 AI grades per month</li>
              <li>1 collection (25 items max)</li>
              <li>Device text-to-speech only</li>
              <li>Marketplace browsing</li>
            </ul>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-6 mt-4 border border-amber-500/30">
            <h3 className="text-lg font-semibold text-amber-400">Pro ($9.99/month)</h3>
            <ul className="list-disc pl-6 mt-2 space-y-1">
              <li>50 AI grades per month</li>
              <li>Unlimited collections</li>
              <li>BREE voice (30 TTS/month)</li>
              <li>Sell on marketplace (5 listings)</li>
              <li>Counterfeit detection (5/month)</li>
            </ul>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-6 mt-4">
            <h3 className="text-lg font-semibold text-amber-400">Master ($24.99/month)</h3>
            <ul className="list-disc pl-6 mt-2 space-y-1">
              <li>200 AI grades per month</li>
              <li>Unlimited TTS voices</li>
              <li>Priority grading queue</li>
              <li>Unlimited marketplace listings</li>
              <li>API access</li>
              <li>Batch grading (10 at once)</li>
            </ul>
          </div>
          <p className="mt-4 text-sm text-slate-400">
            Annual subscriptions receive 33% discount. Subscriptions are billed through the Apple App Store.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">5. Marketplace Rules</h2>
          <ul className="list-disc pl-6 space-y-2">
            <li>All items listed must be accurately described and photographed.</li>
            <li>Sellers are responsible for item authenticity and condition.</li>
            <li>EPOCGS is not responsible for disputes between buyers and sellers.</li>
            <li>Fraudulent listings will result in account termination.</li>
            <li>EPOCGS may take a commission on marketplace sales (currently 0%).</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">6. User Conduct</h2>
          <p>You agree not to:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Upload fraudulent, fake, or misleading collectible images.</li>
            <li>Misrepresent AI grades as official professional grades.</li>
            <li>Sell counterfeit items on the marketplace.</li>
            <li>Abuse the grading system or attempt to manipulate results.</li>
            <li>Share your account credentials with others.</li>
            <li>Use the service for any illegal purpose.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">7. Intellectual Property</h2>
          <p>
            You retain ownership of your collectible photos and collection data. By using EPOCGS,
            you grant us a license to process your images for grading purposes. We do not claim
            ownership of your content.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">8. Cancellation & Refunds</h2>
          <ul className="list-disc pl-6 space-y-2">
            <li>You may cancel your subscription at any time.</li>
            <li>Refunds are handled by Apple according to their refund policy.</li>
            <li>Unused grade credits do not carry over after cancellation.</li>
            <li>Your collection data remains accessible on the free tier after cancellation.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">9. Limitation of Liability</h2>
          <p>
            EPOCGS is provided &quot;as is&quot; without warranties of any kind. We are not liable for:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Inaccurate AI grades or valuations.</li>
            <li>Loss of data due to service interruptions.</li>
            <li>Marketplace disputes between users.</li>
            <li>Financial losses based on our grade estimates.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">10. Changes to Terms</h2>
          <p>
            We reserve the right to modify these terms at any time. Continued use of the service
            after changes constitutes acceptance of the new terms.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">11. Governing Law</h2>
          <p>
            These terms are governed by the laws of the State of Texas, United States.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">12. Contact</h2>
          <p>
            For questions about these terms, contact us at:
          </p>
          <p className="mt-4">
            <strong>Email:</strong> support@echo-op.com<br />
            <strong>Company:</strong> Echo Omega Prime<br />
            <strong>Location:</strong> Midland, TX 79705
          </p>
        </section>
      </div>
    </div>
  );
}
