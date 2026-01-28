'use client';

export default function PrivacyPage() {
  return (
    <div className="container mx-auto px-4 py-12 max-w-4xl">
      <h1 className="text-4xl font-bold text-white mb-8">Privacy Policy</h1>
      <div className="prose prose-invert prose-purple max-w-none space-y-6 text-slate-300">
        <p className="text-slate-400">Last updated: January 4, 2026</p>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">1. Information We Collect</h2>
          <p>
            EPOCGS (&quot;Echo Prime Omega Collectibles Grading System&quot;) collects the following information:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong>Account Information:</strong> Email address, display name, and profile photo when you sign in with Google.</li>
            <li><strong>Collection Data:</strong> Photos, grades, and metadata of collectibles you upload for grading.</li>
            <li><strong>Usage Data:</strong> Grading history, marketplace activity, and app usage statistics.</li>
            <li><strong>Device Information:</strong> Device type, operating system, and app version for technical support.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">2. How We Use Your Information</h2>
          <ul className="list-disc pl-6 space-y-2">
            <li>To provide AI-powered grading services using Gemini Vision and other AI models.</li>
            <li>To sync your collection across devices via Firebase Cloud.</li>
            <li>To enable marketplace features for buying and selling collectibles.</li>
            <li>To generate voice commentary using ElevenLabs text-to-speech.</li>
            <li>To improve our grading accuracy and service quality.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">3. Data Storage & Security</h2>
          <p>
            Your data is stored securely using Google Firebase with enterprise-grade security:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>All data is encrypted in transit (TLS 1.3) and at rest.</li>
            <li>Authentication is handled by Firebase Auth with Google Sign-In.</li>
            <li>Images are stored in Firebase Storage with access controls.</li>
            <li>We do not sell your personal information to third parties.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">4. Third-Party Services</h2>
          <p>We use the following third-party services:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong>Google Firebase:</strong> Authentication, database, and storage.</li>
            <li><strong>Google Gemini:</strong> AI vision grading analysis.</li>
            <li><strong>Together.ai:</strong> Pricing analysis via Llama 3.3.</li>
            <li><strong>ElevenLabs:</strong> Voice synthesis for audio commentary.</li>
            <li><strong>Apple App Store:</strong> Payment processing for subscriptions.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">5. Your Rights</h2>
          <p>You have the right to:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Access and download your collection data at any time.</li>
            <li>Delete your account and all associated data.</li>
            <li>Export your grading history as PDF or CSV.</li>
            <li>Opt out of analytics and promotional communications.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">6. Data Retention</h2>
          <p>
            We retain your data for as long as your account is active. If you delete your account,
            we will delete your personal information within 30 days, except where required by law.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">7. Children&apos;s Privacy</h2>
          <p>
            EPOCGS is not intended for children under 13. We do not knowingly collect
            personal information from children under 13 years of age.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">8. Changes to This Policy</h2>
          <p>
            We may update this privacy policy from time to time. We will notify you of any
            changes by posting the new policy on this page and updating the &quot;Last updated&quot; date.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">9. Contact Us</h2>
          <p>
            If you have questions about this privacy policy, please contact us at:
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
