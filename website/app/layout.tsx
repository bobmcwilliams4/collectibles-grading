'use client';

import './globals.css';
import { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { onAuthChange, signOut, signInWithGoogle } from '@/lib/firebase';
import { useAuthStore } from '@/lib/store';

function Navigation() {
  const pathname = usePathname();
  const { user, loading, setUser } = useAuthStore();

  useEffect(() => {
    const unsubscribe = onAuthChange((user) => {
      setUser(user);
    });
    return () => unsubscribe();
  }, [setUser]);

  const handleSignIn = async () => {
    try {
      await signInWithGoogle();
    } catch (error) {
      console.error('Sign in error:', error);
    }
  };

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (error) {
      console.error('Sign out error:', error);
    }
  };

  const navLinks = [
    { href: '/', label: 'Home' },
    { href: '/marketplace', label: 'Marketplace' },
    { href: '/services', label: 'Services' },
    { href: '/showcase', label: 'Showcase' },
    { href: '/download', label: 'Download' },
  ];

  if (user) {
    navLinks.splice(1, 0, { href: '/collection', label: 'My Collection' });
  }

  return (
    <header className="sticky top-0 z-50 border-b border-purple-500/20 bg-slate-900/80 backdrop-blur-xl">
      <nav className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center glow-purple">
              <span className="text-xl font-bold text-white">E</span>
            </div>
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">
                EPOCGS
              </h1>
              <p className="text-xs text-slate-400">Collectibles Grader</p>
            </div>
          </Link>

          {/* Nav Links */}
          <div className="hidden md:flex items-center gap-2">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`nav-link ${pathname === link.href ? 'active' : ''}`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Auth */}
          <div className="flex items-center gap-4">
            {loading ? (
              <div className="w-8 h-8 rounded-full bg-slate-700 animate-pulse" />
            ) : user ? (
              <div className="flex items-center gap-3">
                <img
                  src={user.photoURL || '/avatar.png'}
                  alt={user.displayName || 'User'}
                  className="w-8 h-8 rounded-full border border-purple-500/50"
                />
                <span className="hidden md:block text-sm text-slate-300">
                  {user.displayName?.split(' ')[0]}
                </span>
                <button
                  onClick={handleSignOut}
                  className="omega-button-secondary text-sm px-4 py-2"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <button onClick={handleSignIn} className="omega-button text-sm px-4 py-2">
                Sign In
              </button>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
}

function Footer() {
  return (
    <footer className="border-t border-purple-500/20 bg-slate-900/50 mt-auto">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-lg font-bold text-white mb-4">EPOCGS</h3>
            <p className="text-slate-400 text-sm">
              Echo Prime Omega Collectibles Grading System. AI-powered grading for comics, cards, coins, stamps, and vinyl.
            </p>
          </div>
          <div>
            <h4 className="font-semibold text-white mb-3">Platform</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li><Link href="/download" className="hover:text-purple-400">Desktop App</Link></li>
              <li><Link href="/marketplace" className="hover:text-purple-400">Marketplace</Link></li>
              <li><Link href="/services" className="hover:text-purple-400">Voice Services</Link></li>
              <li><Link href="/showcase" className="hover:text-purple-400">Showcase</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-white mb-3">Support</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li><a href="#" className="hover:text-purple-400">Documentation</a></li>
              <li><a href="#" className="hover:text-purple-400">Contact</a></li>
              <li><a href="#" className="hover:text-purple-400">FAQ</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-white mb-3">Legal</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li><Link href="/privacy" className="hover:text-purple-400">Privacy Policy</Link></li>
              <li><Link href="/terms" className="hover:text-purple-400">Terms of Service</Link></li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t border-slate-800 text-center text-sm text-slate-500">
          <p>ECHO OMEGA PRIME | Authority Level 11.0 SOVEREIGN</p>
          <p className="mt-1">AI-Verified Grades | Multi-Model Consensus (Claude, Gemini, GPT)</p>
        </div>
      </div>
    </footer>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <title>EPOCGS - Collectibles Grading System</title>
        <meta name="description" content="AI-Powered Collectibles Grading System with marketplace" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="min-h-screen flex flex-col matrix-grid">
        <Navigation />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
