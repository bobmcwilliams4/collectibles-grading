'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { getPublicShowcase } from '@/lib/firebase';

interface ShowcaseCollection {
  id: string;
  userId: string;
  userName: string;
  userAvatar?: string;
  totalItems: number;
  totalValue: number;
  topGrade?: number;
  featuredItems: {
    id: string;
    title: string;
    type: string;
    grade?: number;
    imageUrl?: string;
  }[];
  specialties: string[];
  badges: string[];
}

// Mock data for showcase (in production, this comes from Firebase)
const mockShowcase: ShowcaseCollection[] = [
  {
    id: '1',
    userId: 'user1',
    userName: 'ComicKing42',
    userAvatar: '',
    totalItems: 347,
    totalValue: 125000,
    topGrade: 9.8,
    featuredItems: [
      { id: '1', title: 'Amazing Spider-Man #300', type: 'comic', grade: 9.8 },
      { id: '2', title: 'X-Men #1 (1963)', type: 'comic', grade: 9.4 },
      { id: '3', title: 'Batman #1', type: 'comic', grade: 8.5 },
    ],
    specialties: ['Marvel', 'Golden Age', 'Key Issues'],
    badges: ['Top Collector', 'Verified Seller', 'Early Adopter'],
  },
  {
    id: '2',
    userId: 'user2',
    userName: 'CardMaster_Pro',
    userAvatar: '',
    totalItems: 1245,
    totalValue: 89000,
    topGrade: 10.0,
    featuredItems: [
      { id: '1', title: '1st Edition Charizard', type: 'card', grade: 10.0 },
      { id: '2', title: 'Black Lotus (Beta)', type: 'card', grade: 9.5 },
      { id: '3', title: 'Michael Jordan Rookie', type: 'card', grade: 9.8 },
    ],
    specialties: ['Pokemon', 'MTG', 'Sports Cards'],
    badges: ['Diamond Seller', 'Card Expert'],
  },
  {
    id: '3',
    userId: 'user3',
    userName: 'VinylVault',
    userAvatar: '',
    totalItems: 523,
    totalValue: 45000,
    topGrade: 9.6,
    featuredItems: [
      { id: '1', title: 'The Beatles - White Album', type: 'vinyl', grade: 9.6 },
      { id: '2', title: 'Pink Floyd - Dark Side', type: 'vinyl', grade: 9.4 },
      { id: '3', title: 'Led Zeppelin I', type: 'vinyl', grade: 9.2 },
    ],
    specialties: ['Classic Rock', 'First Pressings', '70s'],
    badges: ['Vinyl Expert', 'Audiophile'],
  },
];

function getGradeClass(grade?: number): string {
  if (!grade) return '';
  if (grade >= 9.8) return 'grade-gem';
  if (grade >= 9.4) return 'grade-mint';
  if (grade >= 9.0) return 'grade-nm';
  if (grade >= 8.0) return 'grade-vf';
  if (grade >= 6.0) return 'grade-fine';
  return 'grade-low';
}

function getTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    comic: '📚',
    card: '🎴',
    coin: '🪙',
    stamp: '📮',
    vinyl: '💿',
  };
  return icons[type] || '📦';
}

function CollectorCard({ collection }: { collection: ShowcaseCollection }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="omega-card overflow-hidden"
    >
      {/* Header */}
      <div className="p-6 border-b border-slate-700/50">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-2xl">
            {collection.userAvatar ? (
              <img src={collection.userAvatar} alt="" className="w-full h-full rounded-full object-cover" />
            ) : (
              collection.userName.charAt(0).toUpperCase()
            )}
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-bold text-white">{collection.userName}</h3>
            <div className="flex flex-wrap gap-2 mt-2">
              {collection.badges.map(badge => (
                <span key={badge} className="px-2 py-0.5 bg-purple-500/20 border border-purple-500/30 rounded-full text-xs text-purple-300">
                  {badge}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 border-b border-slate-700/50">
        <div className="p-4 text-center border-r border-slate-700/50">
          <div className="text-2xl font-bold text-white">{collection.totalItems.toLocaleString()}</div>
          <div className="text-xs text-slate-400">Items</div>
        </div>
        <div className="p-4 text-center border-r border-slate-700/50">
          <div className="text-2xl font-bold text-green-400">${(collection.totalValue / 1000).toFixed(0)}K</div>
          <div className="text-xs text-slate-400">Value</div>
        </div>
        <div className="p-4 text-center">
          <div className={`text-2xl font-bold ${getGradeClass(collection.topGrade)} bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-green-500`}>
            {collection.topGrade?.toFixed(1) || 'N/A'}
          </div>
          <div className="text-xs text-slate-400">Top Grade</div>
        </div>
      </div>

      {/* Featured Items */}
      <div className="p-4">
        <h4 className="text-sm font-semibold text-slate-400 mb-3">Featured Items</h4>
        <div className="space-y-2">
          {collection.featuredItems.map(item => (
            <div key={item.id} className="flex items-center gap-3 p-2 rounded-lg bg-slate-800/50">
              <span className="text-xl">{getTypeIcon(item.type)}</span>
              <span className="flex-1 text-sm text-white truncate">{item.title}</span>
              {item.grade && (
                <span className={`grade-badge text-xs ${getGradeClass(item.grade)}`}>
                  {item.grade.toFixed(1)}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Specialties */}
      <div className="px-4 pb-4">
        <div className="flex flex-wrap gap-2">
          {collection.specialties.map(spec => (
            <span key={spec} className="px-3 py-1 bg-slate-700/50 rounded-full text-xs text-slate-300">
              {spec}
            </span>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-slate-700/50 flex gap-2">
        <button className="flex-1 omega-button text-sm py-2">View Collection</button>
        <button className="flex-1 omega-button-secondary text-sm py-2">Follow</button>
      </div>
    </motion.div>
  );
}

export default function ShowcasePage() {
  const [collections, setCollections] = useState<ShowcaseCollection[]>(mockShowcase);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState<'value' | 'items' | 'grade'>('value');

  useEffect(() => {
    // In production, fetch from Firebase
    // const loadShowcase = async () => {
    //   setLoading(true);
    //   const data = await getPublicShowcase();
    //   setCollections(data);
    //   setLoading(false);
    // };
    // loadShowcase();
  }, []);

  const sortedCollections = [...collections].sort((a, b) => {
    if (sortBy === 'value') return b.totalValue - a.totalValue;
    if (sortBy === 'items') return b.totalItems - a.totalItems;
    if (sortBy === 'grade') return (b.topGrade || 0) - (a.topGrade || 0);
    return 0;
  });

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="text-4xl lg:text-5xl font-bold text-white mb-4">
            Collector Showcase
          </h1>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            Discover amazing collections from verified collectors around the world.
            Get inspired and connect with fellow enthusiasts.
          </p>
        </motion.div>
      </div>

      {/* Stats Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="omega-card p-6 text-center"
        >
          <div className="text-3xl font-bold text-purple-400">2,547</div>
          <div className="text-sm text-slate-400">Active Collectors</div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="omega-card p-6 text-center"
        >
          <div className="text-3xl font-bold text-cyan-400">127K+</div>
          <div className="text-sm text-slate-400">Items Graded</div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="omega-card p-6 text-center"
        >
          <div className="text-3xl font-bold text-green-400">$4.2M</div>
          <div className="text-sm text-slate-400">Total Value</div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="omega-card p-6 text-center"
        >
          <div className="text-3xl font-bold text-amber-400">9.4</div>
          <div className="text-sm text-slate-400">Avg. Grade</div>
        </motion.div>
      </div>

      {/* Sort Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <h2 className="text-2xl font-bold text-white">Top Collections</h2>
        <div className="flex gap-2">
          {[
            { value: 'value' as const, label: 'By Value', icon: '💰' },
            { value: 'items' as const, label: 'By Items', icon: '📦' },
            { value: 'grade' as const, label: 'By Grade', icon: '⭐' },
          ].map(option => (
            <button
              key={option.value}
              onClick={() => setSortBy(option.value)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                sortBy === option.value
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              <span className="mr-2">{option.icon}</span>
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Collections Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="omega-card animate-pulse">
              <div className="p-6 border-b border-slate-700/50">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-slate-700" />
                  <div className="flex-1 space-y-2">
                    <div className="h-5 bg-slate-700 rounded w-1/2" />
                    <div className="h-3 bg-slate-700 rounded w-3/4" />
                  </div>
                </div>
              </div>
              <div className="p-4 space-y-3">
                <div className="h-10 bg-slate-700 rounded" />
                <div className="h-10 bg-slate-700 rounded" />
                <div className="h-10 bg-slate-700 rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedCollections.map((collection, index) => (
            <motion.div
              key={collection.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <CollectorCard collection={collection} />
            </motion.div>
          ))}
        </div>
      )}

      {/* CTA Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="mt-16 text-center"
      >
        <div className="omega-card p-12 max-w-2xl mx-auto">
          <h3 className="text-2xl font-bold text-white mb-4">
            Want to showcase your collection?
          </h3>
          <p className="text-slate-400 mb-6">
            Sign up, add your collectibles, and get AI-powered grades to join the showcase.
            It's free to get started!
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <a href="/download" className="omega-button">Download App</a>
            <a href="/collection" className="omega-button-secondary">Start Grading</a>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
